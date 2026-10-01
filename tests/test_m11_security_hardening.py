"""SecureVault — Milestone M11 Security Hardening Regression Tests.

Validates the security fixes and invariant hardening introduced in M11:
  1. Deterministic KEK memory zeroing on mutable bytearray buffers (M11.1 / SEC-M11-01)
     - create_vault()
     - unlock_vault()
     - change_master_password()
  2. Transient master password buffer zeroing in KDF (M11.2 / SEC-M11-02)
  3. Atomic in-memory state update rollback on save_vault() failure (M11.3 / SEC-M11-03)
  4. Constant-time password reuse comparison using hmac.compare_digest (M11.4 / SEC-M11-04)
"""

from __future__ import annotations

import hmac
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.core.config import AppConfig
from app.core.exceptions import (
    AuthenticationError,
    InvalidPasswordInputError,
    PasswordReuseError,
    StorageError,
)
from app.crypto.encryption import zero_buffer
from app.crypto.kdf import KDFParameters, derive_kek, generate_salt
from app.services.vault_service import DecryptedVault, VaultService


@pytest.fixture
def fast_params() -> KDFParameters:
    """Fast Argon2id parameters for testing."""
    return KDFParameters.fast_for_testing()


@pytest.fixture
def temp_vault_env(tmp_path: Path):
    """Fixture providing isolated AppConfig and VaultService."""
    data_dir = tmp_path / "securevault_data"
    data_dir.mkdir(parents=True, exist_ok=True)
    config = AppConfig(data_dir=data_dir)
    vault_service = VaultService(config=config)
    return config, vault_service, data_dir / "test_vault.svault"


# ==============================================================================
# 1. KEK MEMORY ZEROING TESTS (M11.1 / SEC-M11-01)
# ==============================================================================

class TestKEKMemoryZeroing:
    """Verifies that all derived KEK buffers are mutable and wiped via zero_buffer()."""

    def test_create_vault_zeroes_mutable_kek(
        self, temp_vault_env, fast_params: KDFParameters
    ) -> None:
        _, vault_service, vault_path = temp_vault_env
        zeroed_buffers: list[tuple[type, int, bytes]] = []

        real_zero = zero_buffer

        def spy_zero_buffer(buf):
            if isinstance(buf, (bytearray, memoryview)):
                # Capture snapshot before zeroing
                zeroed_buffers.append((type(buf), len(buf), bytes(buf)))
            real_zero(buf)

        with patch("app.services.vault_service.zero_buffer", side_effect=spy_zero_buffer):
            vault = vault_service.create_vault(
                master_password="ValidMasterPassword123!",
                vault_path=vault_path,
                kdf_params=fast_params,
            )

        assert vault is not None
        assert vault_path.exists()

        # Find the 32-byte KEK buffer passed to zero_buffer
        kek_zeroings = [
            (buf_type, length, snapshot)
            for buf_type, length, snapshot in zeroed_buffers
            if length == 32 and buf_type is bytearray
        ]
        assert len(kek_zeroings) >= 1, "Expected zero_buffer() to be called on a 32-byte bytearray KEK"
        # Verify the captured pre-zero snapshot was non-zero
        assert any(snap != b"\x00" * 32 for _, _, snap in kek_zeroings)

    def test_unlock_vault_zeroes_mutable_kek(
        self, temp_vault_env, fast_params: KDFParameters
    ) -> None:
        _, vault_service, vault_path = temp_vault_env
        vault_service.create_vault(
            master_password="ValidMasterPassword123!",
            vault_path=vault_path,
            kdf_params=fast_params,
        )
        vault_service.lock_vault()

        zeroed_buffers: list[tuple[type, int, bytes]] = []
        real_zero = zero_buffer

        def spy_zero_buffer(buf):
            if isinstance(buf, (bytearray, memoryview)):
                zeroed_buffers.append((type(buf), len(buf), bytes(buf)))
            real_zero(buf)

        with patch("app.services.vault_service.zero_buffer", side_effect=spy_zero_buffer):
            unlocked = vault_service.unlock_vault(
                master_password="ValidMasterPassword123!",
                vault_path=vault_path,
            )

        assert unlocked is not None

        # Verify a 32-byte mutable bytearray KEK was zeroed
        kek_zeroings = [
            (buf_type, length, snapshot)
            for buf_type, length, snapshot in zeroed_buffers
            if length == 32 and buf_type is bytearray
        ]
        assert len(kek_zeroings) >= 1, "Expected zero_buffer() to be called on mutable KEK during unlock"
        assert any(snap != b"\x00" * 32 for _, _, snap in kek_zeroings)

    def test_unlock_vault_zeroes_kek_on_wrong_password_failure(
        self, temp_vault_env, fast_params: KDFParameters
    ) -> None:
        _, vault_service, vault_path = temp_vault_env
        vault_service.create_vault(
            master_password="CorrectPassword123!",
            vault_path=vault_path,
            kdf_params=fast_params,
        )
        vault_service.lock_vault()

        zeroed_buffers: list[tuple[type, int]] = []
        real_zero = zero_buffer

        def spy_zero_buffer(buf):
            if isinstance(buf, (bytearray, memoryview)):
                zeroed_buffers.append((type(buf), len(buf)))
            real_zero(buf)

        with patch("app.services.vault_service.zero_buffer", side_effect=spy_zero_buffer):
            with pytest.raises(AuthenticationError):
                vault_service.unlock_vault(
                    master_password="WrongPassword999!",
                    vault_path=vault_path,
                )

        # Confirm KEK was wiped even when unlock failed
        assert any(length == 32 and buf_type is bytearray for buf_type, length in zeroed_buffers)

    def test_change_master_password_zeroes_all_transient_keys(
        self, temp_vault_env, fast_params: KDFParameters
    ) -> None:
        _, vault_service, vault_path = temp_vault_env
        vault_service.create_vault(
            master_password="OldPassword123!",
            vault_path=vault_path,
            kdf_params=fast_params,
        )

        zeroed_buffers: list[tuple[type, int]] = []
        real_zero = zero_buffer

        def spy_zero_buffer(buf):
            if isinstance(buf, (bytearray, memoryview)):
                zeroed_buffers.append((type(buf), len(buf)))
            real_zero(buf)

        with patch("app.services.vault_service.zero_buffer", side_effect=spy_zero_buffer):
            vault_service.change_master_password(
                current_password="OldPassword123!",
                new_password="NewPassword456!",
                confirm_password="NewPassword456!",
                vault_path=vault_path,
            )

        # change_master_password must zero: cur_kek (32B), new_kek (32B), dek_buffer (32B)
        kek_zeroings = [
            (buf_type, length)
            for buf_type, length in zeroed_buffers
            if length == 32 and buf_type is bytearray
        ]
        # At minimum: cur_kek, new_kek, dek_buffer = 3 zeroing calls
        assert len(kek_zeroings) >= 3, f"Expected at least 3 zeroing calls of 32-byte buffers, got {len(kek_zeroings)}"


# ==============================================================================
# 2. KDF TRANSIENT PASSWORD BUFFER ZEROING (M11.2 / SEC-M11-02)
# ==============================================================================

class TestKDFPasswordBufferZeroing:
    """Verifies that derive_kek() holds password in a mutable bytearray and zeroes it."""

    def test_kdf_transient_password_buffer_is_zeroed(
        self, fast_params: KDFParameters
    ) -> None:
        salt = generate_salt()
        pwd = "EphemeralPassword987!"
        expected_len = len(pwd.encode("utf-8"))

        zeroed_buffers: list[tuple[type, int, bytes]] = []
        real_zero = zero_buffer

        def spy_zero_buffer(buf):
            if isinstance(buf, (bytearray, memoryview)):
                zeroed_buffers.append((type(buf), len(buf), bytes(buf)))
            real_zero(buf)

        with patch("app.crypto.kdf.zero_buffer", side_effect=spy_zero_buffer):
            kek = derive_kek(pwd, salt, fast_params)

        assert len(kek) == 32
        # Check that a bytearray of expected_len was passed to zero_buffer
        pwd_zeroings = [
            (buf_type, length, snapshot)
            for buf_type, length, snapshot in zeroed_buffers
            if length == expected_len and buf_type is bytearray
        ]
        assert len(pwd_zeroings) == 1, "Expected exactly one zeroing of the transient password bytearray"
        assert pwd_zeroings[0][2] == pwd.encode("utf-8"), "Pre-zero buffer contained the raw password bytes"

    def test_kdf_as_bytearray_option(self, fast_params: KDFParameters) -> None:
        salt = generate_salt()
        # Default returns immutable bytes
        kek_bytes = derive_kek("TestPassword123!", salt, fast_params, as_bytearray=False)
        assert isinstance(kek_bytes, bytes)
        assert not isinstance(kek_bytes, bytearray)

        # as_bytearray=True returns mutable bytearray
        kek_bytearray = derive_kek("TestPassword123!", salt, fast_params, as_bytearray=True)
        assert isinstance(kek_bytearray, bytearray)
        assert len(kek_bytearray) == 32
        # Can be zeroed in-place
        zero_buffer(kek_bytearray)
        assert kek_bytearray == bytearray(32)


# ==============================================================================
# 3. ATOMIC IN-MEMORY STATE UPDATE ROLLBACK (M11.3 / SEC-M11-03)
# ==============================================================================

class TestSaveVaultAtomicity:
    """Verifies that failure in save_vault() does not mutate in-memory vault state."""

    def test_save_vault_failure_does_not_mutate_in_memory_state(
        self, temp_vault_env, fast_params: KDFParameters
    ) -> None:
        _, vault_service, vault_path = temp_vault_env
        vault = vault_service.create_vault(
            master_password="Password123!",
            vault_path=vault_path,
            kdf_params=fast_params,
        )

        original_updated_at = vault.payload["updated_at"]
        original_header = vault.header
        original_raw_json = vault.raw_json

        # Simulate a disk write failure during save_vault()
        with patch(
            "app.services.vault_service.write_vault_file",
            side_effect=StorageError("Disk full simulation"),
        ):
            with pytest.raises(StorageError, match="Disk full simulation"):
                vault_service.save_vault()

        # Verify that in-memory payload, header, and raw_json remained untouched
        assert vault.payload["updated_at"] == original_updated_at
        assert vault.header == original_header
        assert vault.raw_json == original_raw_json

    def test_save_vault_success_commits_in_memory_state(
        self, temp_vault_env, fast_params: KDFParameters
    ) -> None:
        _, vault_service, vault_path = temp_vault_env
        vault = vault_service.create_vault(
            master_password="Password123!",
            vault_path=vault_path,
            kdf_params=fast_params,
        )

        original_updated_at = vault.payload["updated_at"]

        # Successful save
        vault_service.save_vault()

        # In-memory updated_at should now be updated
        assert vault.payload["updated_at"] != original_updated_at


# ==============================================================================
# 4. CONSTANT-TIME PASSWORD REUSE COMPARISON (M11.4 / SEC-M11-04)
# ==============================================================================

class TestConstantTimePasswordReuse:
    """Verifies constant-time comparison in master password rotation."""

    def test_identical_passwords_raise_password_reuse_error(
        self, temp_vault_env, fast_params: KDFParameters
    ) -> None:
        _, vault_service, vault_path = temp_vault_env
        vault_service.create_vault(
            master_password="CurrentPassword123!",
            vault_path=vault_path,
            kdf_params=fast_params,
        )

        compare_digest_called = False
        real_compare = hmac.compare_digest

        def spy_compare(a, b):
            nonlocal compare_digest_called
            compare_digest_called = True
            return real_compare(a, b)

        with patch("hmac.compare_digest", side_effect=spy_compare):
            with pytest.raises(PasswordReuseError) as exc_info:
                vault_service.change_master_password(
                    current_password="CurrentPassword123!",
                    new_password="CurrentPassword123!",
                    confirm_password="CurrentPassword123!",
                    vault_path=vault_path,
                )

        assert compare_digest_called is True
        # Verify backwards compatibility with InvalidPasswordInputError
        assert isinstance(exc_info.value, InvalidPasswordInputError)
        assert "cannot be the same as the current password" in str(exc_info.value)

"""SecureVault — Unit & Integration Tests for VaultService & Atomic Persistence.

Verifies:
  - End-to-end vault creation and disk persistence.
  - Successful unlock with correct master password.
  - Authentication failure on wrong master password (authenticated DEK unwrap).
  - Robust corruption handling (magic, wrapped DEK, DEK tag, payload, payload tag, truncation).
  - Missing file handling (VaultNotFoundError).
  - Atomic write temporary file handling.
  - Best-effort in-memory key clearing on session lock.
  - Strict security verification: vault file contains ZERO plaintext passwords, keys, or JSON.
"""

from pathlib import Path
import json
import pytest

from app.core.config import AppConfig
from app.core.exceptions import (
    AuthenticationError,
    CorruptedVaultError,
    InvalidPasswordInputError,
    InvalidVaultFormatError,
    VaultNotFoundError,
)
from app.crypto.kdf import KDFParameters
from app.services.vault_service import DecryptedVault, VaultService, create_empty_vault_payload
from app.storage.vault_format import HEADER_SIZE


@pytest.fixture
def fast_kdf_params() -> KDFParameters:
    return KDFParameters.fast_for_testing()


@pytest.fixture
def vault_dir(tmp_path: Path) -> Path:
    target_dir = tmp_path / "vault_storage"
    return target_dir


@pytest.fixture
def vault_service(vault_dir: Path) -> VaultService:
    config = AppConfig(data_dir=vault_dir)
    return VaultService(config=config)


class TestEmptyVaultPayload:
    """Test minimal initial JSON payload envelope."""

    def test_empty_payload_structure(self) -> None:
        payload_bytes = create_empty_vault_payload()
        assert isinstance(payload_bytes, bytes)
        data = json.loads(payload_bytes.decode("utf-8"))

        assert data["schema_version"] == 1
        assert "vault_id" in data
        assert "created_at" in data
        assert "updated_at" in data
        assert data["items"] == []


class TestVaultLifecycle:
    """Test end-to-end vault creation, unlock, and lock lifecycle."""

    def test_create_and_unlock_vault(
        self,
        vault_service: VaultService,
        fast_kdf_params: KDFParameters,
    ) -> None:
        password = "CorrectHorseBatteryStaple!2026"
        vault_path = vault_service.config.vault_path

        assert not vault_path.exists()
        assert not vault_service.is_vault_created()

        # 1. Create Vault
        created_vault = vault_service.create_vault(
            master_password=password,
            kdf_params=fast_kdf_params,
        )

        assert vault_path.exists()
        assert vault_service.is_vault_created()
        assert isinstance(created_vault, DecryptedVault)
        assert created_vault.is_locked is False
        assert created_vault.item_count == 0
        assert len(created_vault.vault_id) > 0

        # File size must be exactly 134 bytes + payload ciphertext
        file_size = vault_path.stat().st_size
        assert file_size == HEADER_SIZE + created_vault.header.payload_len

        # 2. Unlock Vault with Correct Password
        unlocked_vault = vault_service.unlock_vault(password)
        assert unlocked_vault.is_locked is False
        assert unlocked_vault.vault_id == created_vault.vault_id
        assert unlocked_vault.item_count == 0
        assert unlocked_vault.payload["schema_version"] == 1

        # 3. Lock Vault
        created_vault.lock()
        assert created_vault.is_locked is True
        assert all(b == 0 for b in created_vault.dek)

        vault_service.lock_vault()
        assert unlocked_vault.is_locked is True
        assert all(b == 0 for b in unlocked_vault.dek)
        assert unlocked_vault.item_count == 0
        assert vault_service.active_vault is None

    def test_unlock_wrong_password_fails(
        self,
        vault_service: VaultService,
        fast_kdf_params: KDFParameters,
    ) -> None:
        correct_password = "CorrectPassword123!"
        wrong_password = "WrongPassword456!"

        vault_service.create_vault(correct_password, kdf_params=fast_kdf_params)

        with pytest.raises(AuthenticationError, match="Incorrect master password"):
            vault_service.unlock_vault(wrong_password)

    def test_create_empty_password_rejected(self, vault_service: VaultService) -> None:
        with pytest.raises(InvalidPasswordInputError, match="cannot be empty"):
            vault_service.create_vault("")

    def test_unlock_empty_password_rejected(self, vault_service: VaultService) -> None:
        with pytest.raises(InvalidPasswordInputError, match="cannot be empty"):
            vault_service.unlock_vault("")

    def test_unlock_missing_file_raises_vault_not_found(self, vault_service: VaultService) -> None:
        with pytest.raises(VaultNotFoundError, match="Vault file not found"):
            vault_service.unlock_vault("AnyPassword123!")


class TestVaultCorruptionHandling:
    """Test fail-secure rejection of tampered or truncated vault files."""

    @pytest.fixture
    def created_vault_file(
        self,
        vault_service: VaultService,
        fast_kdf_params: KDFParameters,
    ) -> tuple[Path, str]:
        password = "TestMasterPassword#1"
        vault = vault_service.create_vault(password, kdf_params=fast_kdf_params)
        return vault.vault_path, password

    def test_corrupted_magic_rejected(
        self,
        vault_service: VaultService,
        created_vault_file: tuple[Path, str],
    ) -> None:
        vault_path, password = created_vault_file
        data = bytearray(vault_path.read_bytes())
        data[0:4] = b"CORR"
        vault_path.write_bytes(data)

        with pytest.raises(InvalidVaultFormatError, match="Invalid vault magic"):
            vault_service.unlock_vault(password)

    def test_corrupted_wrapped_dek_rejected(
        self,
        vault_service: VaultService,
        created_vault_file: tuple[Path, str],
    ) -> None:
        vault_path, password = created_vault_file
        data = bytearray(vault_path.read_bytes())
        # WRAPPED_DEK offset is 0x32 (50)
        data[50] ^= 0xFF
        vault_path.write_bytes(data)

        with pytest.raises(AuthenticationError, match="Incorrect master password"):
            vault_service.unlock_vault(password)

    def test_corrupted_dek_tag_rejected(
        self,
        vault_service: VaultService,
        created_vault_file: tuple[Path, str],
    ) -> None:
        vault_path, password = created_vault_file
        data = bytearray(vault_path.read_bytes())
        # DEK_TAG offset is 0x52 (82)
        data[82] ^= 0xFF
        vault_path.write_bytes(data)

        with pytest.raises(AuthenticationError, match="Incorrect master password"):
            vault_service.unlock_vault(password)

    def test_corrupted_payload_ciphertext_rejected(
        self,
        vault_service: VaultService,
        created_vault_file: tuple[Path, str],
    ) -> None:
        vault_path, password = created_vault_file
        data = bytearray(vault_path.read_bytes())
        # Payload ciphertext starts at offset 134 (0x86)
        data[134] ^= 0xFF
        vault_path.write_bytes(data)

        with pytest.raises(CorruptedVaultError, match="authentication failed or corrupted"):
            vault_service.unlock_vault(password)

    def test_corrupted_payload_tag_rejected(
        self,
        vault_service: VaultService,
        created_vault_file: tuple[Path, str],
    ) -> None:
        vault_path, password = created_vault_file
        data = bytearray(vault_path.read_bytes())
        # PAYLOAD_TAG offset is 0x76 (118)
        data[118] ^= 0xFF
        vault_path.write_bytes(data)

        with pytest.raises(CorruptedVaultError, match="authentication failed or corrupted"):
            vault_service.unlock_vault(password)

    def test_truncated_payload_rejected(
        self,
        vault_service: VaultService,
        created_vault_file: tuple[Path, str],
    ) -> None:
        vault_path, password = created_vault_file
        data = vault_path.read_bytes()
        # Truncate by 5 bytes
        vault_path.write_bytes(data[:-5])

        with pytest.raises(CorruptedVaultError, match="payload length mismatch"):
            vault_service.unlock_vault(password)


class TestAtomicPersistence:
    """Test filesystem durability and temporary file handling."""

    def test_atomic_write_leaves_no_temp_file(
        self,
        vault_service: VaultService,
        fast_kdf_params: KDFParameters,
    ) -> None:
        vault_path = vault_service.config.vault_path
        tmp_path = vault_path.with_name(f"{vault_path.name}.tmp")

        vault_service.create_vault("Password123!", kdf_params=fast_kdf_params)

        assert vault_path.exists()
        assert not tmp_path.exists()


class TestSecuritySecrecy:
    """Test that secrets are NEVER written to disk in the .svault file."""

    def test_vault_file_contains_no_plaintext_secrets(
        self,
        vault_service: VaultService,
        fast_kdf_params: KDFParameters,
    ) -> None:
        password = "VeryUniqueSuperSecretPasswordToDetect#99"
        vault = vault_service.create_vault(password, kdf_params=fast_kdf_params)

        raw_file_bytes = vault.vault_path.read_bytes()

        # 1. Master password must NOT be in the file
        assert password.encode("utf-8") not in raw_file_bytes

        # 2. Raw DEK bytes must NOT be in the file
        raw_dek = bytes(vault.dek)
        assert raw_dek not in raw_file_bytes

        # 3. JSON payload strings must NOT be visible in ciphertext
        assert b"schema_version" not in raw_file_bytes
        assert b"vault_id" not in raw_file_bytes
        assert b"items" not in raw_file_bytes

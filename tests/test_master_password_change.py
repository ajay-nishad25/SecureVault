"""Tests for Master Password Change and Cryptographic DEK Re-Wrapping (Milestone M8).

Verifies:
    1. Empty current password rejected with InvalidPasswordInputError
    2. Incorrect current password rejected with AuthenticationError; vault untouched
    3. Empty new password rejected with InvalidPasswordInputError
    4. Short new password (< 8 chars) rejected with InvalidPasswordInputError
    5. Confirmation mismatch rejected with InvalidPasswordInputError
    6. New password identical to current password rejected with InvalidPasswordInputError
    7. Successful password change updates vault file on disk
    8. Old master password fails authentication after change
    9. New master password succeeds and unlocks vault
    10. Vault ID is preserved across password change
    11. Existing credentials and decrypted secrets are preserved across change
    12. Failed password change leaves original vault completely intact and usable
    13. Atomic persistence leaves no temporary files on disk
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from app.core.config import AppConfig
from app.core.exceptions import AuthenticationError, InvalidPasswordInputError
from app.crypto.kdf import KDFParameters
from app.models.credential import Credential
from app.services.credential_service import CredentialService
from app.services.vault_service import DecryptedVault, VaultService
from app.storage.vault_file import read_vault_file
from app.storage.vault_format import VaultHeader


@pytest.fixture
def vault_with_items(tmp_path: Path):
    """Fixture providing an unlocked vault populated with credentials."""
    config = AppConfig(data_dir=tmp_path)
    vault_service = VaultService(config)

    vault = vault_service.create_vault(
        "CurrentPass123!",
        kdf_params=KDFParameters.fast_for_testing(),
    )
    cred_service = CredentialService(vault_service)
    cred1 = cred_service.create_credential(
        title="GitHub",
        username="octocat",
        password="github-secret-pass",
        notes="Work repos",
    )
    cred2 = cred_service.create_credential(
        title="Google",
        username="user@example.com",
        password="google-secret-pass",
        notes="Personal email",
    )

    return config, vault_service, cred_service, vault, [cred1, cred2]


def test_empty_current_password_rejected(vault_with_items) -> None:
    """1. Verify empty current password raises InvalidPasswordInputError."""
    _, vault_service, _, _, _ = vault_with_items

    with pytest.raises(InvalidPasswordInputError, match="Current master password cannot be empty"):
        vault_service.change_master_password(
            current_password="",
            new_password="NewValidPass456!",
            confirm_password="NewValidPass456!",
        )


def test_incorrect_current_password_rejected(vault_with_items) -> None:
    """2. Verify wrong current password raises AuthenticationError and leaves vault untouched."""
    config, vault_service, _, vault, _ = vault_with_items
    original_header_bytes, original_payload = read_vault_file(config.vault_path)

    with pytest.raises(AuthenticationError, match="Incorrect current master password"):
        vault_service.change_master_password(
            current_password="WrongCurrentPassword!",
            new_password="NewValidPass456!",
            confirm_password="NewValidPass456!",
        )

    # Vault on disk is completely untouched
    after_header_bytes, after_payload = read_vault_file(config.vault_path)
    assert original_header_bytes == after_header_bytes
    assert original_payload == after_payload

    # Old password still unlocks
    unlocked = vault_service.unlock_vault("CurrentPass123!")
    assert unlocked.vault_id == vault.vault_id


def test_empty_new_password_rejected(vault_with_items) -> None:
    """3. Verify empty new password raises InvalidPasswordInputError."""
    _, vault_service, _, _, _ = vault_with_items

    with pytest.raises(InvalidPasswordInputError, match="Master password cannot be empty"):
        vault_service.change_master_password(
            current_password="CurrentPass123!",
            new_password="",
            confirm_password="",
        )


def test_short_new_password_rejected(vault_with_items) -> None:
    """4. Verify new password shorter than 8 characters is rejected."""
    _, vault_service, _, _, _ = vault_with_items

    with pytest.raises(InvalidPasswordInputError, match="at least 8 characters"):
        vault_service.change_master_password(
            current_password="CurrentPass123!",
            new_password="short",
            confirm_password="short",
        )


def test_password_confirmation_mismatch_rejected(vault_with_items) -> None:
    """5. Verify mismatched new passwords raise InvalidPasswordInputError."""
    _, vault_service, _, _, _ = vault_with_items

    with pytest.raises(InvalidPasswordInputError, match="Passwords do not match"):
        vault_service.change_master_password(
            current_password="CurrentPass123!",
            new_password="NewValidPass456!",
            confirm_password="DifferentPass789!",
        )


def test_same_password_rejected(vault_with_items) -> None:
    """6. Verify changing to the same password is explicitly rejected."""
    _, vault_service, _, _, _ = vault_with_items

    with pytest.raises(InvalidPasswordInputError, match="cannot be the same as the current password"):
        vault_service.change_master_password(
            current_password="CurrentPass123!",
            new_password="CurrentPass123!",
            confirm_password="CurrentPass123!",
        )


def test_successful_password_change_flow(vault_with_items) -> None:
    """7-11. Verify successful password change, credential preservation, and authentication transition."""
    config, vault_service, cred_service, vault, original_items = vault_with_items
    original_vault_id = vault.vault_id

    # Read original file bytes to verify cryptographic header change
    old_header_bytes, old_payload_ciphertext = read_vault_file(config.vault_path)
    old_header = VaultHeader.parse(old_header_bytes)

    # Change password
    vault_service.change_master_password(
        current_password="CurrentPass123!",
        new_password="BrandNewPass456!",
        confirm_password="BrandNewPass456!",
    )

    # Verify vault file header changed (new salt, new wrapped_dek)
    new_header_bytes, new_payload_ciphertext = read_vault_file(config.vault_path)
    new_header = VaultHeader.parse(new_header_bytes)

    assert new_header.salt != old_header.salt
    assert new_header.wrapped_dek != old_header.wrapped_dek
    # Payload ciphertext remains IDENTICAL (DEK was re-wrapped, not recreated)
    assert new_payload_ciphertext == old_payload_ciphertext
    assert new_header.payload_nonce == old_header.payload_nonce
    assert new_header.payload_tag == old_header.payload_tag

    # Lock session
    vault_service.lock_vault()

    # Old password MUST fail
    with pytest.raises(AuthenticationError):
        vault_service.unlock_vault("CurrentPass123!")

    # New password MUST unlock
    new_vault = vault_service.unlock_vault("BrandNewPass456!")
    assert new_vault.vault_id == original_vault_id
    assert new_vault.item_count == len(original_items)

    # Verify credentials intact
    new_cred_service = CredentialService(vault_service)
    items = new_cred_service.get_all_credentials()
    assert len(items) == 2

    cred_map = {item.title: item for item in items}
    assert "GitHub" in cred_map
    assert cred_map["GitHub"].username == "octocat"
    assert cred_map["GitHub"].password == "github-secret-pass"
    assert cred_map["GitHub"].notes == "Work repos"

    assert "Google" in cred_map
    assert cred_map["Google"].username == "user@example.com"
    assert cred_map["Google"].password == "google-secret-pass"


def test_atomic_persistence_leaves_no_temp_files(vault_with_items) -> None:
    """12. Verify password change operates atomically and leaves no .tmp files."""
    config, vault_service, _, _, _ = vault_with_items

    vault_service.change_master_password(
        current_password="CurrentPass123!",
        new_password="NewSecurePass789!",
        confirm_password="NewSecurePass789!",
    )

    tmp_files = list(config.data_dir.glob("*.tmp"))
    assert len(tmp_files) == 0

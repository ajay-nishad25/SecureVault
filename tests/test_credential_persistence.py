"""End-to-end encrypted persistence & reload tests for credentials (Milestone 5)."""

from pathlib import Path
import pytest

from app.core.config import AppConfig
from app.crypto.kdf import KDFParameters
from app.services.credential_service import CredentialService
from app.services.vault_service import VaultService


def test_create_save_lock_unlock_reload_lifecycle(tmp_path: Path) -> None:
    """Verify: Create credential -> Lock vault -> Unlock vault -> Read credential.

    Asserts that the credential survives memory clearing and application lock/unlock.
    """
    config = AppConfig(data_dir=tmp_path)
    vault_service = VaultService(config)
    master_password = "MasterPassword2026!"

    # 1. Initialize vault
    vault_service.create_vault(
        master_password=master_password,
        kdf_params=KDFParameters.fast_for_testing(),
    )
    cred_service = CredentialService(vault_service)

    # 2. Create credential
    created = cred_service.create_credential(
        title="ProtonMail",
        username="user@proton.me",
        password="ProtonSecretPassword#2026",
        notes="Encrypted mailbox",
    )
    original_id = created.id

    # 3. Lock vault (in-memory keys zeroed and dereferenced)
    vault_service.lock_vault()
    assert vault_service.active_vault is None

    # 4. Re-open vault using master password
    unlocked_vault = vault_service.unlock_vault(master_password)
    assert unlocked_vault is not None
    assert unlocked_vault.item_count == 1

    # 5. Read credential via fresh CredentialService
    reloaded_service = CredentialService(vault_service)
    fetched = reloaded_service.get_credential(original_id)

    assert fetched is not None
    assert fetched.id == original_id
    assert fetched.title == "ProtonMail"
    assert fetched.username == "user@proton.me"
    assert fetched.password == "ProtonSecretPassword#2026"
    assert fetched.notes == "Encrypted mailbox"


def test_create_update_save_lock_unlock_reload_lifecycle(tmp_path: Path) -> None:
    """Verify: Create -> Update -> Lock -> Unlock -> Verify updated credential."""
    config = AppConfig(data_dir=tmp_path)
    vault_service = VaultService(config)
    master_password = "MasterPassword2026!"

    vault_service.create_vault(
        master_password=master_password,
        kdf_params=KDFParameters.fast_for_testing(),
    )
    cred_service = CredentialService(vault_service)

    # 1. Create
    created = cred_service.create_credential(
        title="InitialTitle",
        username="initial_user",
        password="InitialPassword!",
        notes="Old note",
    )
    cred_id = created.id

    # 2. Update
    cred_service.update_credential(
        credential_id=cred_id,
        title="UpdatedTitle",
        username="updated_user",
        password="UpdatedPassword!",
        notes="New note",
    )

    # 3. Lock
    vault_service.lock_vault()

    # 4. Unlock
    vault_service.unlock_vault(master_password)
    reloaded_service = CredentialService(vault_service)

    # 5. Verify updated fields
    fetched = reloaded_service.get_credential(cred_id)
    assert fetched is not None
    assert fetched.id == cred_id
    assert fetched.title == "UpdatedTitle"
    assert fetched.username == "updated_user"
    assert fetched.password == "UpdatedPassword!"
    assert fetched.notes == "New note"


def test_create_delete_save_lock_unlock_reload_lifecycle(tmp_path: Path) -> None:
    """Verify: Create 2 credentials -> Delete 1 -> Lock -> Unlock -> Verify deletion persisted."""
    config = AppConfig(data_dir=tmp_path)
    vault_service = VaultService(config)
    master_password = "MasterPassword2026!"

    vault_service.create_vault(
        master_password=master_password,
        kdf_params=KDFParameters.fast_for_testing(),
    )
    cred_service = CredentialService(vault_service)

    c1 = cred_service.create_credential("KeepMe", "user1", "pass1")
    c2 = cred_service.create_credential("DeleteMe", "user2", "pass2")

    # Delete c2
    cred_service.delete_credential(c2.id)

    # Lock & Reload
    vault_service.lock_vault()
    vault_service.unlock_vault(master_password)

    reloaded_service = CredentialService(vault_service)
    all_creds = reloaded_service.get_all_credentials()

    assert len(all_creds) == 1
    assert all_creds[0].id == c1.id
    assert reloaded_service.get_credential(c2.id) is None


def test_plaintext_password_is_never_written_to_raw_vault_file(tmp_path: Path) -> None:
    """Verify that neither master password nor credential passwords appear in raw file bytes."""
    config = AppConfig(data_dir=tmp_path)
    vault_service = VaultService(config)
    master_password = "MasterPasswordTopSecret#2026"
    credential_password = "SuperSecretCredentialPassword!12345"

    vault_service.create_vault(
        master_password=master_password,
        kdf_params=KDFParameters.fast_for_testing(),
    )
    cred_service = CredentialService(vault_service)

    cred_service.create_credential(
        title="SensitiveBank",
        username="bank_user",
        password=credential_password,
    )

    vault_file_bytes = config.vault_path.read_bytes()

    # Neither password should exist anywhere in the raw binary file on disk
    assert master_password.encode("utf-8") not in vault_file_bytes
    assert credential_password.encode("utf-8") not in vault_file_bytes
    assert b"SensitiveBank" not in vault_file_bytes
    assert b"bank_user" not in vault_file_bytes

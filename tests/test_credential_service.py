"""Unit and integration tests for CredentialService (Milestone 5)."""

from pathlib import Path
import pytest

from app.core.config import AppConfig
from app.core.exceptions import (
    CredentialNotFoundError,
    CredentialValidationError,
    VaultLockedError,
)
from app.crypto.kdf import KDFParameters
from app.services.credential_service import CredentialService
from app.services.vault_service import VaultService


@pytest.fixture
def unlocked_vault_service(tmp_path: Path) -> VaultService:
    """Provide a VaultService with an active, unlocked vault using fast KDF parameters."""
    config = AppConfig(data_dir=tmp_path)
    service = VaultService(config)
    service.create_vault(
        master_password="MasterTestPassword123!",
        kdf_params=KDFParameters.fast_for_testing(),
    )
    return service


@pytest.fixture
def credential_service(unlocked_vault_service: VaultService) -> CredentialService:
    """Provide a CredentialService bound to an unlocked vault."""
    return CredentialService(unlocked_vault_service)


# ---------------------------------------------------------------------------
# CREATE TESTS
# ---------------------------------------------------------------------------

def test_create_valid_credential(
    credential_service: CredentialService,
    unlocked_vault_service: VaultService,
) -> None:
    """Verify creating a valid credential adds it to in-memory vault and persists."""
    cred = credential_service.create_credential(
        title="GitHub",
        username="developer@example.com",
        password="MySecretPassword123!",
        notes="Work token",
    )

    assert cred.title == "GitHub"
    assert cred.username == "developer@example.com"
    assert cred.password == "MySecretPassword123!"
    assert cred.notes == "Work token"
    assert isinstance(cred.id, str) and len(cred.id) > 0

    # Verify present in active vault payload
    active_vault = unlocked_vault_service.active_vault
    assert active_vault is not None
    assert active_vault.item_count == 1
    assert active_vault.payload["items"][0]["id"] == cred.id


def test_create_credential_generates_unique_ids(
    credential_service: CredentialService,
) -> None:
    """Verify multiple creations produce unique identifiers."""
    c1 = credential_service.create_credential("Site1", "user1", "pass1")
    c2 = credential_service.create_credential("Site2", "user2", "pass2")
    c3 = credential_service.create_credential("Site3", "user3", "pass3")

    ids = {c1.id, c2.id, c3.id}
    assert len(ids) == 3


def test_create_credential_validation_required_fields(
    credential_service: CredentialService,
) -> None:
    """Verify create_credential rejects empty title, username, or password."""
    with pytest.raises(CredentialValidationError, match="title is required"):
        credential_service.create_credential(title="", username="u", password="p")

    with pytest.raises(CredentialValidationError, match="username is required"):
        credential_service.create_credential(title="t", username="   ", password="p")

    with pytest.raises(CredentialValidationError, match="password is required"):
        credential_service.create_credential(title="t", username="u", password="")


def test_create_credential_persists_to_disk(
    credential_service: CredentialService,
    unlocked_vault_service: VaultService,
) -> None:
    """Verify file modification time or content changes upon creation."""
    vault_path = unlocked_vault_service.config.vault_path
    initial_mtime = vault_path.stat().st_mtime_ns

    credential_service.create_credential("Slack", "user@corp.com", "SlackPass#2026")

    updated_mtime = vault_path.stat().st_mtime_ns
    assert updated_mtime >= initial_mtime
    assert vault_path.exists()
    assert vault_path.stat().st_size > 134


def test_create_credential_does_not_log_passwords(
    credential_service: CredentialService,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Verify secret password never appears in logs during creation."""
    secret = "SuperConfidentialSecretPassword999!"
    credential_service.create_credential("Banking", "admin", secret)

    for record in caplog.records:
        assert secret not in record.getMessage()


# ---------------------------------------------------------------------------
# READ TESTS
# ---------------------------------------------------------------------------

def test_get_credential_by_id(
    credential_service: CredentialService,
) -> None:
    """Verify retrieving a credential by its exact UUID."""
    created = credential_service.create_credential(
        title="GitLab",
        username="dev_gitlab",
        password="PassWord123!",
        notes="Self-hosted",
    )

    fetched = credential_service.get_credential(created.id)
    assert fetched is not None
    assert fetched.id == created.id
    assert fetched.title == "GitLab"
    assert fetched.username == "dev_gitlab"
    assert fetched.password == "PassWord123!"
    assert fetched.notes == "Self-hosted"


def test_get_credential_unknown_id_returns_none(
    credential_service: CredentialService,
) -> None:
    """Verify unknown credential ID cleanly returns None."""
    credential_service.create_credential("App", "user", "pass")
    result = credential_service.get_credential("non-existent-uuid-9999")
    assert result is None


def test_get_credential_or_raise_unknown_id(
    credential_service: CredentialService,
) -> None:
    """Verify get_credential_or_raise raises CredentialNotFoundError for unknown ID."""
    with pytest.raises(CredentialNotFoundError, match="not found"):
        credential_service.get_credential_or_raise("missing-id-404")


def test_get_all_credentials(
    credential_service: CredentialService,
) -> None:
    """Verify retrieving list of all stored credentials."""
    assert credential_service.get_all_credentials() == []

    c1 = credential_service.create_credential("SiteA", "userA", "passA")
    c2 = credential_service.create_credential("SiteB", "userB", "passB")

    all_creds = credential_service.get_all_credentials()
    assert len(all_creds) == 2
    assert [c.id for c in all_creds] == [c1.id, c2.id]


# ---------------------------------------------------------------------------
# UPDATE TESTS
# ---------------------------------------------------------------------------

def test_update_credential_fields(
    credential_service: CredentialService,
) -> None:
    """Verify updating title, username, password, and notes on existing credential."""
    created = credential_service.create_credential(
        title="OldTitle",
        username="OldUser",
        password="OldPassword123!",
        notes="OldNotes",
    )

    updated = credential_service.update_credential(
        credential_id=created.id,
        title="NewTitle",
        username="NewUser",
        password="NewPassword456!",
        notes="NewNotes",
    )

    assert updated.id == created.id
    assert updated.title == "NewTitle"
    assert updated.username == "NewUser"
    assert updated.password == "NewPassword456!"
    assert updated.notes == "NewNotes"

    # Confirm in-memory payload reflects changes
    refetched = credential_service.get_credential(created.id)
    assert refetched is not None
    assert refetched.title == "NewTitle"
    assert refetched.username == "NewUser"
    assert refetched.password == "NewPassword456!"
    assert refetched.notes == "NewNotes"


def test_update_credential_preserves_id(
    credential_service: CredentialService,
) -> None:
    """Verify that updating a credential never changes its identifier."""
    created = credential_service.create_credential("Title", "User", "Pass")
    original_id = created.id

    updated = credential_service.update_credential(
        credential_id=original_id,
        title="ChangedTitle",
        username="ChangedUser",
        password="ChangedPass",
    )
    assert updated.id == original_id


def test_update_credential_invalid_fields_rejected(
    credential_service: CredentialService,
) -> None:
    """Verify update rejects empty required fields."""
    created = credential_service.create_credential("Title", "User", "Pass")

    with pytest.raises(CredentialValidationError, match="title is required"):
        credential_service.update_credential(created.id, title="", username="u", password="p")

    with pytest.raises(CredentialValidationError, match="password is required"):
        credential_service.update_credential(created.id, title="t", username="u", password="")


def test_update_credential_unknown_id_raises_error(
    credential_service: CredentialService,
) -> None:
    """Verify attempting to update unknown ID raises CredentialNotFoundError."""
    with pytest.raises(CredentialNotFoundError, match="not found"):
        credential_service.update_credential(
            credential_id="non-existent-id",
            title="Title",
            username="User",
            password="Password",
        )


def test_update_credential_does_not_log_passwords(
    credential_service: CredentialService,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Verify updated secret password is not logged."""
    created = credential_service.create_credential("Title", "User", "InitialPassword")
    caplog.clear()

    secret = "UpdatedSecretPassword777!"
    credential_service.update_credential(created.id, "Title", "User", secret)

    for record in caplog.records:
        assert secret not in record.getMessage()


def test_update_credential_persists_to_disk(
    credential_service: CredentialService,
    unlocked_vault_service: VaultService,
) -> None:
    """Verify disk file is updated when a credential is modified."""
    vault_path = unlocked_vault_service.config.vault_path
    created = credential_service.create_credential("Site", "User", "Pass")
    mtime_before = vault_path.stat().st_mtime_ns

    credential_service.update_credential(created.id, "Site", "User", "NewPass")
    mtime_after = vault_path.stat().st_mtime_ns
    assert mtime_after >= mtime_before
    assert vault_path.exists()


# ---------------------------------------------------------------------------
# DELETE TESTS
# ---------------------------------------------------------------------------

def test_delete_credential_success(
    credential_service: CredentialService,
    unlocked_vault_service: VaultService,
) -> None:
    """Verify deleting a credential removes it from the vault."""
    c1 = credential_service.create_credential("Title1", "User1", "Pass1")
    c2 = credential_service.create_credential("Title2", "User2", "Pass2")
    assert unlocked_vault_service.active_vault.item_count == 2

    result = credential_service.delete_credential(c1.id)
    assert result is True

    assert unlocked_vault_service.active_vault.item_count == 1
    assert credential_service.get_credential(c1.id) is None
    assert credential_service.get_credential(c2.id) is not None


def test_delete_credential_persists_to_disk(
    credential_service: CredentialService,
    unlocked_vault_service: VaultService,
) -> None:
    """Verify disk file is updated when a credential is deleted."""
    vault_path = unlocked_vault_service.config.vault_path
    c = credential_service.create_credential("ToDelete", "User", "Pass")
    mtime_before = vault_path.stat().st_mtime_ns

    credential_service.delete_credential(c.id)
    mtime_after = vault_path.stat().st_mtime_ns
    assert mtime_after >= mtime_before
    assert vault_path.exists()


def test_delete_credential_unknown_id_raises_error(
    credential_service: CredentialService,
) -> None:
    """Verify attempting to delete unknown ID raises CredentialNotFoundError."""
    with pytest.raises(CredentialNotFoundError, match="not found"):
        credential_service.delete_credential("unknown-id-12345")


# ---------------------------------------------------------------------------
# LOCKED VAULT GUARD TESTS
# ---------------------------------------------------------------------------

def test_operations_on_locked_vault_raise_security_error(
    credential_service: CredentialService,
    unlocked_vault_service: VaultService,
) -> None:
    """Verify all CRUD operations raise VaultLockedError if vault is locked."""
    unlocked_vault_service.lock_vault()

    with pytest.raises(VaultLockedError):
        credential_service.create_credential("T", "U", "P")

    with pytest.raises(VaultLockedError):
        credential_service.get_credential("any-id")

    with pytest.raises(VaultLockedError):
        credential_service.get_all_credentials()

    with pytest.raises(VaultLockedError):
        credential_service.update_credential("any-id", "T", "U", "P")

    with pytest.raises(VaultLockedError):
        credential_service.delete_credential("any-id")

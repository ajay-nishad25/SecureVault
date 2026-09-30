"""Tests for Credential domain model (Milestone 5)."""

import uuid
import pytest

from app.core.exceptions import CredentialValidationError
from app.models.credential import Credential


def test_credential_creation_valid() -> None:
    """Verify creating a credential with valid parameters."""
    cred = Credential(
        title="GitHub",
        username="alice@example.com",
        password="SuperSecretPassword123!",
        notes="Personal account token",
    )

    assert cred.title == "GitHub"
    assert cred.username == "alice@example.com"
    assert cred.password == "SuperSecretPassword123!"
    assert cred.notes == "Personal account token"
    assert isinstance(cred.id, str)
    assert len(cred.id) > 0
    # Must be valid UUID
    uuid.UUID(cred.id)


def test_credential_id_generation_unique() -> None:
    """Verify that auto-generated IDs are unique for each instance."""
    cred1 = Credential(title="Site1", username="user1", password="pw1")
    cred2 = Credential(title="Site2", username="user2", password="pw2")

    assert cred1.id != cred2.id


def test_credential_missing_title_raises_error() -> None:
    """Verify empty or whitespace-only title raises CredentialValidationError."""
    with pytest.raises(CredentialValidationError, match="title is required"):
        Credential(title="", username="alice", password="secretpassword")

    with pytest.raises(CredentialValidationError, match="title is required"):
        Credential(title="   ", username="alice", password="secretpassword")


def test_credential_missing_username_raises_error() -> None:
    """Verify empty or whitespace-only username raises CredentialValidationError."""
    with pytest.raises(CredentialValidationError, match="username is required"):
        Credential(title="GitHub", username="", password="secretpassword")

    with pytest.raises(CredentialValidationError, match="username is required"):
        Credential(title="GitHub", username="   ", password="secretpassword")


def test_credential_missing_password_raises_error() -> None:
    """Verify empty password raises CredentialValidationError."""
    with pytest.raises(CredentialValidationError, match="password is required"):
        Credential(title="GitHub", username="alice", password="")


def test_credential_optional_notes() -> None:
    """Verify notes field is optional and defaults to empty string."""
    cred = Credential(title="GitHub", username="alice", password="secretpassword")
    assert cred.notes == ""

    cred_with_notes = Credential(
        title="GitHub",
        username="alice",
        password="secretpassword",
        notes="Custom notes",
    )
    assert cred_with_notes.notes == "Custom notes"


def test_credential_serialization_contains_exact_fields() -> None:
    """Verify to_dict produces exactly the documented schema fields with no extra properties."""
    cred = Credential(
        id="test-id-123",
        title="AWS Console",
        username="admin",
        password="ComplexAwsPassword#99",
        notes="Production root",
    )

    data = cred.to_dict()

    assert data == {
        "id": "test-id-123",
        "title": "AWS Console",
        "username": "admin",
        "password": "ComplexAwsPassword#99",
        "notes": "Production root",
    }
    # Enforce strict field set: no 'type', no 'category', no timestamps
    assert set(data.keys()) == {"id", "title", "username", "password", "notes"}
    assert "type" not in data
    assert "category" not in data


def test_credential_deserialization_valid() -> None:
    """Verify from_dict parses valid dictionary data cleanly."""
    payload = {
        "id": "550e8400-e29b-41d4-a716-446655440000",
        "title": "GitLab",
        "username": "bob",
        "password": "MyGitLabPassword123!",
        "notes": "CI token included",
    }

    cred = Credential.from_dict(payload)

    assert cred.id == "550e8400-e29b-41d4-a716-446655440000"
    assert cred.title == "GitLab"
    assert cred.username == "bob"
    assert cred.password == "MyGitLabPassword123!"
    assert cred.notes == "CI token included"


def test_credential_deserialization_missing_notes_defaults_empty() -> None:
    """Verify from_dict gracefully handles omitted or None notes field."""
    payload = {
        "id": "item-uuid-1",
        "title": "Service",
        "username": "user",
        "password": "pass",
    }
    cred = Credential.from_dict(payload)
    assert cred.notes == ""

    payload_none = {
        "id": "item-uuid-2",
        "title": "Service",
        "username": "user",
        "password": "pass",
        "notes": None,
    }
    cred_none = Credential.from_dict(payload_none)
    assert cred_none.notes == ""


def test_credential_deserialization_invalid() -> None:
    """Verify from_dict rejects malformed dictionary input."""
    # Non-dictionary
    with pytest.raises(CredentialValidationError, match="must be a dictionary"):
        Credential.from_dict(["not", "a", "dict"])  # type: ignore

    # Missing ID
    with pytest.raises(CredentialValidationError, match="missing valid 'id'"):
        Credential.from_dict({"title": "T", "username": "U", "password": "P"})

    # Empty required title
    with pytest.raises(CredentialValidationError, match="title is required"):
        Credential.from_dict({"id": "1", "title": "", "username": "U", "password": "P"})

    # Empty required password
    with pytest.raises(CredentialValidationError, match="password is required"):
        Credential.from_dict({"id": "1", "title": "T", "username": "U", "password": ""})


def test_credential_repr_masks_password() -> None:
    """Verify that Credential __repr__ never leaks plaintext passwords."""
    raw_secret = "UltraSecretPassword999!"
    cred = Credential(title="Banking", username="user", password=raw_secret)

    repr_str = repr(cred)
    assert raw_secret not in repr_str
    assert "password='***'" in repr_str
    assert "Banking" in repr_str

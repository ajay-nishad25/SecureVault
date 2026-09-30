"""SecureVault — Credential Domain Model.

Represents an individual credential record stored in the encrypted vault payload.
Strictly adheres to the Milestone 5 specification:
  - id: Auto-generated unique identifier
  - title: REQUIRED non-empty string
  - username: REQUIRED non-empty string
  - password: REQUIRED non-empty string
  - notes: OPTIONAL string (defaults to "")

Security Rules:
  - No type, category, or tags fields in M5.
  - No plaintext logging of passwords in __repr__ or __str__.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any

from app.core.exceptions import CredentialValidationError
from app.core.validation import validate_credential


@dataclass
class Credential:
    """Individual credential entity stored within the encrypted vault payload."""

    title: str
    username: str
    password: str
    notes: str = ""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))

    def __post_init__(self) -> None:
        """Validate fields upon initialization."""
        self.validate()

    def validate(self) -> None:
        """Validate credential required fields and types.

        Raises:
            CredentialValidationError: If any required field is empty or invalid.
        """
        is_valid, error_msg = validate_credential(
            title=self.title,
            username=self.username,
            password=self.password,
            notes=self.notes,
        )
        if not is_valid:
            raise CredentialValidationError(error_msg)

        if not isinstance(self.id, str) or not self.id.strip():
            raise CredentialValidationError("Credential ID must be a non-empty string.")

    def to_dict(self) -> dict[str, Any]:
        """Serialize the credential to a JSON-compatible dictionary."""
        return {
            "id": self.id,
            "title": self.title.strip(),
            "username": self.username.strip(),
            "password": self.password,
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Credential:
        """Deserialize a credential instance from a dictionary.

        Args:
            data: Dictionary containing credential fields.

        Returns:
            Credential: Validated credential instance.

        Raises:
            CredentialValidationError: If data is not a dict or lacks required fields.
        """
        if not isinstance(data, dict):
            raise CredentialValidationError("Credential data must be a dictionary.")

        raw_id = data.get("id")
        if not raw_id or not isinstance(raw_id, str):
            raise CredentialValidationError("Credential data missing valid 'id' field.")

        title = data.get("title", "")
        username = data.get("username", "")
        password = data.get("password", "")
        notes = data.get("notes", "")

        return cls(
            id=str(raw_id),
            title=title,
            username=username,
            password=password,
            notes=notes if notes is not None else "",
        )

    def __repr__(self) -> str:
        """Masked representation to prevent accidental secret leakage in logs/traces."""
        return (
            f"Credential(id={self.id!r}, title={self.title!r}, "
            f"username={self.username!r}, password='***', notes={self.notes!r})"
        )

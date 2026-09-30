"""SecureVault — Credential CRUD Service.

Orchestrates credential lifecycle operations on the active, unlocked vault:
  - CREATE: Validate, assign unique ID, append, persist under AES-256-GCM.
  - READ: Fetch by ID or list all credentials from the active DecryptedVault.
  - UPDATE: Validate, update record in-place, persist under AES-256-GCM.
  - DELETE: Remove record from in-memory collection, persist under AES-256-GCM.

CRITICAL SECURITY RULES:
  - Passwords and secrets are NEVER logged or written to unencrypted storage.
  - Operations require an active, unlocked vault session.
  - All modifications persist atomically through VaultService.save_vault().
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from app.core.exceptions import (
    CredentialNotFoundError,
    CredentialValidationError,
    VaultLockedError,
)
from app.core.logging import get_logger
from app.models.credential import Credential

if TYPE_CHECKING:
    from app.services.vault_service import DecryptedVault, VaultService

logger = get_logger("services.credential")


class CredentialService:
    """Manages CRUD operations on credential records within an active vault session."""

    def __init__(self, vault_service: VaultService) -> None:
        self._vault_service = vault_service

    @property
    def vault_service(self) -> VaultService:
        """Return the underlying VaultService instance."""
        return self._vault_service

    def _get_active_vault(self) -> DecryptedVault:
        """Ensure active vault session is present and unlocked.

        Raises:
            VaultLockedError: If vault is locked or not unlocked.
        """
        vault = self._vault_service.active_vault
        if vault is None or vault.is_locked:
            raise VaultLockedError("Cannot perform credential operation: vault is locked.")
        return vault

    def create_credential(
        self,
        title: str,
        username: str,
        password: str,
        notes: str = "",
    ) -> Credential:
        """Create and persist a new credential item in the active vault.

        Args:
            title: Required credential title (e.g., 'GitHub').
            username: Required account identifier / username.
            password: Required secret credential password.
            notes: Optional notes or description.

        Returns:
            Credential: Newly created and persisted credential object.

        Raises:
            CredentialValidationError: If any required field is empty.
            VaultLockedError: If the vault is locked.
            StorageError: If disk persistence fails.
        """
        vault = self._get_active_vault()

        # Instantiate and validate domain model
        credential = Credential(
            title=title,
            username=username,
            password=password,
            notes=notes,
        )

        items = vault.payload.setdefault("items", [])
        existing_ids = {item.get("id") for item in items if isinstance(item, dict)}

        # Ensure ID collision resistance
        while credential.id in existing_ids:
            credential.id = str(uuid.uuid4())

        items.append(credential.to_dict())

        # Persist through existing M4 VaultService
        self._vault_service.save_vault(vault)
        logger.info("Created credential '%s' (ID: %s).", credential.title, credential.id)
        return credential

    def get_credential(self, credential_id: str) -> Credential | None:
        """Retrieve a single credential by ID from the active vault.

        Args:
            credential_id: Unique credential UUID string.

        Returns:
            Credential | None: Credential instance if found, or None if unknown.

        Raises:
            VaultLockedError: If the vault is locked.
        """
        vault = self._get_active_vault()
        items = vault.payload.get("items", [])

        for item in items:
            if isinstance(item, dict) and item.get("id") == credential_id:
                return Credential.from_dict(item)

        return None

    def get_credential_or_raise(self, credential_id: str) -> Credential:
        """Retrieve a credential by ID, raising CredentialNotFoundError if missing.

        Args:
            credential_id: Unique credential UUID string.

        Returns:
            Credential: Found credential instance.

        Raises:
            CredentialNotFoundError: If credential_id does not exist.
            VaultLockedError: If the vault is locked.
        """
        credential = self.get_credential(credential_id)
        if credential is None:
            raise CredentialNotFoundError(f"Credential with ID '{credential_id}' not found.")
        return credential

    def get_all_credentials(self) -> list[Credential]:
        """Retrieve all credentials stored in the active vault.

        Returns:
            list[Credential]: List of all deserialized credentials.

        Raises:
            VaultLockedError: If the vault is locked.
        """
        vault = self._get_active_vault()
        items = vault.payload.get("items", [])
        credentials: list[Credential] = []

        for item in items:
            if isinstance(item, dict):
                try:
                    credentials.append(Credential.from_dict(item))
                except CredentialValidationError as err:
                    logger.warning("Skipping malformed credential in vault payload: %s", err)

        return credentials

    def update_credential(
        self,
        credential_id: str,
        title: str,
        username: str,
        password: str,
        notes: str = "",
    ) -> Credential:
        """Update an existing credential by ID and persist changes.

        Args:
            credential_id: Unique ID of the credential to update.
            title: Updated required title.
            username: Updated required username.
            password: Updated required password.
            notes: Updated optional notes.

        Returns:
            Credential: The updated credential object.

        Raises:
            CredentialNotFoundError: If credential_id does not exist.
            CredentialValidationError: If any required field is empty.
            VaultLockedError: If the vault is locked.
            StorageError: If disk persistence fails.
        """
        vault = self._get_active_vault()
        items = vault.payload.setdefault("items", [])

        target_idx: int | None = None
        for idx, item in enumerate(items):
            if isinstance(item, dict) and item.get("id") == credential_id:
                target_idx = idx
                break

        if target_idx is None:
            raise CredentialNotFoundError(f"Credential with ID '{credential_id}' not found.")

        # Create updated credential entity (validates required fields)
        updated = Credential(
            id=credential_id,
            title=title,
            username=username,
            password=password,
            notes=notes,
        )

        items[target_idx] = updated.to_dict()

        # Persist through existing M4 VaultService
        self._vault_service.save_vault(vault)
        logger.info("Updated credential '%s' (ID: %s).", updated.title, updated.id)
        return updated

    def delete_credential(self, credential_id: str) -> bool:
        """Delete an existing credential by ID and persist changes.

        Args:
            credential_id: Unique ID of the credential to remove.

        Returns:
            bool: True if successfully deleted.

        Raises:
            CredentialNotFoundError: If credential_id does not exist.
            VaultLockedError: If the vault is locked.
            StorageError: If disk persistence fails.
        """
        vault = self._get_active_vault()
        items = vault.payload.setdefault("items", [])

        target_idx: int | None = None
        for idx, item in enumerate(items):
            if isinstance(item, dict) and item.get("id") == credential_id:
                target_idx = idx
                break

        if target_idx is None:
            raise CredentialNotFoundError(f"Credential with ID '{credential_id}' not found.")

        items.pop(target_idx)

        # Persist through existing M4 VaultService
        self._vault_service.save_vault(vault)
        logger.info("Deleted credential with ID: %s.", credential_id)
        return True

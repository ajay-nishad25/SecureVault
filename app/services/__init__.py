"""SecureVault Services Subsystem.

Architectural Boundary:
This package encapsulates application-level domain and auxiliary services:
  - First-run detection and initialization (InitializationService) [M2]
  - Master Password Authentication and KEK lifecycle (AuthenticationService) [M3]
  - Cryptographic vault lifecycle and persistence (VaultService) [M4]
  - Credential CRUD operations and data management (CredentialService) [M5]
  - Clipboard watchdog and auto-clear timer [M10]
  - Inactivity monitoring and auto-lock coordinator [M7]
"""

from app.services.authentication import AuthenticationResult, AuthenticationService
from app.services.credential_service import CredentialService
from app.services.initialization import InitializationService, SessionState
from app.services.vault_service import (
    DecryptedVault,
    VaultService,
    create_empty_vault_payload,
)

__all__ = [
    "AuthenticationService",
    "AuthenticationResult",
    "InitializationService",
    "SessionState",
    "VaultService",
    "DecryptedVault",
    "CredentialService",
    "create_empty_vault_payload",
]

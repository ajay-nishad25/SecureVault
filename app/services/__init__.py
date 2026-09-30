"""SecureVault Services Subsystem.

Architectural Boundary:
This package encapsulates application-level auxiliary services:
  - First-run detection and initialization (InitializationService) [M2]
  - Master Password Authentication and KEK lifecycle (AuthenticationService) [M3]
  - Clipboard watchdog and auto-clear timer (QClipboard) [M10]
  - Inactivity monitoring and auto-lock coordinator [M7]
  - Plaintext CSV export utility [M10]
"""

from app.services.authentication import AuthenticationResult, AuthenticationService
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
    "create_empty_vault_payload",
]

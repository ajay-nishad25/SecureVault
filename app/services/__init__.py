"""SecureVault Services Subsystem.

Architectural Boundary:
This package encapsulates application-level auxiliary services:
  - First-run detection and initialization (InitializationService)
  - Clipboard watchdog and auto-clear timer (QClipboard) [M10]
  - Inactivity monitoring and auto-lock coordinator [M7]
  - Plaintext CSV export utility [M10]
"""

from app.services.initialization import InitializationService, SessionState

__all__ = ["InitializationService", "SessionState"]

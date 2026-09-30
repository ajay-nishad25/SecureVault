"""SecureVault Domain Models.

Architectural Boundary:
This package encapsulates domain data representations:
  - Credential (unique ID, title, username, password, notes)
"""

from app.models.credential import Credential

__all__ = ["Credential"]

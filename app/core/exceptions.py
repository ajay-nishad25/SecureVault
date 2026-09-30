"""SecureVault — Core Exception Hierarchy.

Defines the foundational application exceptions. Specialized errors
(such as AuthenticationError or StorageCorruptionError) inherit from
these base classes in subsequent milestones.
"""


class SecureVaultError(Exception):
    """Base exception for all domain errors in SecureVault."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message

    def __str__(self) -> str:
        return self.message


class ConfigurationError(SecureVaultError):
    """Raised when application configuration is invalid or boundary rules are violated."""


class StorageError(SecureVaultError):
    """Raised when file storage or persistence operations encounter an error."""


class SecurityError(SecureVaultError):
    """Raised when a security boundary, policy, or session constraint is violated."""


class ValidationError(SecureVaultError):
    """Raised when input validation fails."""

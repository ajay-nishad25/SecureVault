"""SecureVault — Core Exception Hierarchy.

Defines the foundational and domain-specific application exceptions.
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


class AuthenticationError(SecurityError):
    """Raised when master authentication fails or cannot be completed."""


class InvalidKDFParametersError(SecurityError):
    """Raised when Argon2id KDF parameters fail bounds or type validation."""


class InvalidSaltError(SecurityError):
    """Raised when a cryptographic salt fails length or validity checks."""


class InvalidPasswordInputError(SecurityError):
    """Raised when password input fails length, format, or validity checks."""


class ValidationError(SecureVaultError):
    """Raised when general input validation fails."""

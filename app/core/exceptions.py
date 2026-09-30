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


class VaultNotFoundError(StorageError):
    """Raised when the specified vault file does not exist on disk."""


class CorruptedVaultError(StorageError):
    """Raised when vault binary data, headers, or payload bounds are corrupted."""


class InvalidVaultFormatError(CorruptedVaultError):
    """Raised when vault magic bytes or format version are invalid or unsupported."""


class SecurityError(SecureVaultError):
    """Raised when a security boundary, policy, or session constraint is violated."""


class DecryptionError(SecurityError):
    """Raised when cryptographic decryption or authentication tag verification fails."""


class AuthenticationError(SecurityError):
    """Raised when master authentication fails or cannot be completed."""


class InvalidKDFParametersError(SecurityError):
    """Raised when Argon2id KDF parameters fail bounds or type validation."""


class InvalidSaltError(SecurityError):
    """Raised when a cryptographic salt fails length or validity checks."""


class InvalidPasswordInputError(SecurityError):
    """Raised when password input fails length, format, or validity checks."""


class VaultLockedError(SecurityError):
    """Raised when an operation requires an unlocked vault but the vault is locked."""


class ValidationError(SecureVaultError):
    """Raised when general input validation fails."""


class CredentialError(SecureVaultError):
    """Base exception for all credential-related operations."""


class CredentialNotFoundError(CredentialError):
    """Raised when a requested credential ID does not exist in the active vault."""


class CredentialValidationError(ValidationError, CredentialError):
    """Raised when credential fields fail validation rules."""


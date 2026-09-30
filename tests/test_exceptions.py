"""Tests for the application exception hierarchy."""

import pytest

from app.core.exceptions import (
    ConfigurationError,
    SecureVaultError,
    SecurityError,
    StorageError,
    ValidationError,
)


def test_exception_inheritance() -> None:
    """Verify that all custom domain exceptions inherit from SecureVaultError."""
    assert issubclass(ConfigurationError, SecureVaultError)
    assert issubclass(StorageError, SecureVaultError)
    assert issubclass(SecurityError, SecureVaultError)
    assert issubclass(ValidationError, SecureVaultError)
    assert issubclass(SecureVaultError, Exception)


def test_exception_instantiation_and_message() -> None:
    """Verify exception message handling and string representation."""
    error = ConfigurationError("Invalid configuration parameter")
    assert str(error) == "Invalid configuration parameter"
    assert error.message == "Invalid configuration parameter"

    with pytest.raises(SecureVaultError) as exc_info:
        raise SecurityError("Access denied")
    assert isinstance(exc_info.value, SecurityError)

"""SecureVault Core Package.

Provides shared application infrastructure: configuration, safe logging,
and domain exception definitions.
"""

from app.core.config import AppConfig, get_default_data_dir, validate_safe_setting_key
from app.core.exceptions import (
    ConfigurationError,
    SecureVaultError,
    SecurityError,
    StorageError,
    ValidationError,
)
from app.core.logging import get_logger, setup_logging

__all__ = [
    "AppConfig",
    "get_default_data_dir",
    "validate_safe_setting_key",
    "SecureVaultError",
    "ConfigurationError",
    "StorageError",
    "SecurityError",
    "ValidationError",
    "get_logger",
    "setup_logging",
]

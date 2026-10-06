"""SecureVault — Application Configuration & Security Boundaries.

This module defines safe, non-sensitive application settings.

CRITICAL SECURITY BOUNDARY:
Under no circumstances may configuration files or this module store:
  - Master passwords
  - Key Encryption Keys (KEK)
  - Data Encryption Keys (DEK)
  - Plaintext credentials, passwords, or notes
  - Authentication tokens or recovery secrets

All sensitive secrets exist strictly in ephemeral session memory and
must NEVER be serialized into configuration files.
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path

from app import __version__
from app.core.exceptions import ConfigurationError

# Explicit blacklist of keywords that must never appear in configuration
PROHIBITED_CONFIG_KEYS: frozenset[str] = frozenset({
    "password",
    "master_password",
    "secret",
    "key",
    "kek",
    "dek",
    "token",
    "credential",
    "recovery",
    "recovery_key",
    "seed",
    "private",
})


def get_default_data_dir() -> Path:
    """Resolve the canonical application data directory across platforms.

    Windows: %LOCALAPPDATA%\\SecureVault
    Linux / Other: ~/.local/share/securevault
    """
    if sys.platform == "win32":
        local_app_data = os.environ.get("LOCALAPPDATA")
        if local_app_data:
            return Path(local_app_data) / "SecureVault"
        return Path.home() / "AppData" / "Local" / "SecureVault"
    return Path.home() / ".local" / "share" / "securevault"


def get_asset_path(filename: str) -> Path:
    """Resolve the path to an asset file across source and packaged runtimes."""
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        base_dir = Path(sys._MEIPASS)  # type: ignore[attr-defined]
    else:
        # Running from source: resolve relative to project root
        base_dir = Path(__file__).resolve().parent.parent.parent
    return base_dir / "assets" / filename


def get_app_icon_path() -> Path:
    """Return the canonical path to the SecureVault application icon (SecureVault.ico)."""
    return get_asset_path("SecureVault.ico")


# Canonical application window dimensions
WINDOW_WIDTH: int = 1100
WINDOW_HEIGHT: int = 780

# Session inactivity timing constants (Milestone M7)
ACTIVITY_GRACE_SECONDS: int = 15
INACTIVITY_TIMEOUT_SECONDS: int = 120


@dataclass(frozen=True)
class AppConfig:
    """Immutable, safe application configuration."""

    app_name: str = "SecureVault"
    app_version: str = __version__
    environment: str = "production"
    data_dir: Path = get_default_data_dir()
    vault_filename: str = "vault.svault"
    settings_filename: str = "settings.json"
    default_auto_lock_minutes: int = 10
    default_clipboard_clear_seconds: int = 30
    log_level: str = "INFO"
    window_width: int = WINDOW_WIDTH
    window_height: int = WINDOW_HEIGHT

    @property
    def vault_path(self) -> Path:
        """Return the absolute path to the encrypted vault file."""
        return self.data_dir / self.vault_filename

    @property
    def settings_path(self) -> Path:
        """Return the absolute path to the non-sensitive settings file."""
        return self.data_dir / self.settings_filename

    @property
    def icon_path(self) -> Path:
        """Return the absolute path to the official application icon (SecureVault.ico)."""
        return get_app_icon_path()

    def ensure_data_dir_exists(self) -> None:
        """Ensure the target application data directory exists."""
        self.data_dir.mkdir(parents=True, exist_ok=True)


def validate_safe_setting_key(key: str) -> None:
    """Validate that a proposed settings key does not violate security boundaries.

    Raises:
        ConfigurationError: If the key contains prohibited sensitive terminology.
    """
    normalized = key.strip().lower()
    for prohibited in PROHIBITED_CONFIG_KEYS:
        if prohibited in normalized:
            raise ConfigurationError(
                f"Security Violation: Key '{key}' violates configuration boundaries. "
                "Sensitive secrets must never be placed in configuration."
            )

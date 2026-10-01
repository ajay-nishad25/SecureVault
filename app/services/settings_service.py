"""SecureVault — Application Settings Service (Milestone M8.1).

Manages non-sensitive application preferences stored in settings.json.

CRITICAL SECURITY BOUNDARY:
settings.json must NEVER contain:
    - Master passwords
    - Key Encryption Keys (KEK)
    - Data Encryption Keys (DEK)
    - Plaintext credentials, passwords, or notes
    - Authentication tokens or recovery secrets

All sensitive secrets exist strictly in ephemeral session memory and
must NEVER be serialized into configuration files.
"""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from app.core.config import AppConfig, validate_safe_setting_key
from app.core.exceptions import ConfigurationError, StorageError
from app.core.logging import get_logger

logger = get_logger("services.settings")

# Default settings values
DEFAULT_THEME: str = "dark"
SUPPORTED_THEMES: tuple[str, ...] = ("dark", "light")

DEFAULT_AUTO_LOCK_TIMEOUT: int = 120  # 2 minutes
SUPPORTED_AUTO_LOCK_TIMEOUTS: tuple[int, ...] = (120, 300, 600, 900)  # 2m, 5m, 10m, 15m


@dataclass(frozen=True)
class AppSettings:
    """Immutable, strongly-typed representation of application preferences."""

    theme: str = DEFAULT_THEME
    auto_lock_timeout: int = DEFAULT_AUTO_LOCK_TIMEOUT

    def to_dict(self) -> dict[str, Any]:
        """Convert settings to dictionary representation."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AppSettings:
        """Create AppSettings from dictionary with validation and safe fallbacks."""
        theme = data.get("theme")
        if theme not in SUPPORTED_THEMES:
            logger.warning(
                "Unsupported or missing theme '%s'. Falling back to default '%s'.",
                theme,
                DEFAULT_THEME,
            )
            theme = DEFAULT_THEME

        auto_lock_timeout = data.get("auto_lock_timeout")
        try:
            auto_lock_timeout = int(auto_lock_timeout)
        except (TypeError, ValueError):
            auto_lock_timeout = DEFAULT_AUTO_LOCK_TIMEOUT

        if auto_lock_timeout not in SUPPORTED_AUTO_LOCK_TIMEOUTS:
            logger.warning(
                "Unsupported auto_lock_timeout '%s'. Falling back to default %d seconds.",
                auto_lock_timeout,
                DEFAULT_AUTO_LOCK_TIMEOUT,
            )
            auto_lock_timeout = DEFAULT_AUTO_LOCK_TIMEOUT

        return cls(theme=theme, auto_lock_timeout=auto_lock_timeout)


class SettingsService:
    """Centralized service for reading, updating, and saving application preferences."""

    def __init__(self, config: AppConfig | None = None) -> None:
        self._config = config or AppConfig()
        self._settings_path: Path = self._config.settings_path
        self._current_settings: AppSettings = self.load_settings()

    @property
    def config(self) -> AppConfig:
        """Return the active configuration."""
        return self._config

    @property
    def settings_path(self) -> Path:
        """Return the settings file path."""
        return self._settings_path

    def get_settings(self) -> AppSettings:
        """Return current in-memory settings."""
        return self._current_settings

    def load_settings(self) -> AppSettings:
        """Load settings from settings.json or create defaults if missing/malformed."""
        if not self._settings_path.exists():
            logger.info(
                "Settings file does not exist at '%s'. Initializing default settings.",
                self._settings_path,
            )
            defaults = AppSettings()
            try:
                self.save_settings(defaults)
            except Exception as err:
                logger.warning("Failed to persist default settings: %s", err)
            self._current_settings = defaults
            return defaults

        try:
            with open(self._settings_path, "r", encoding="utf-8") as f:
                raw_data = json.load(f)

            if not isinstance(raw_data, dict):
                logger.warning(
                    "Settings file content is not a JSON object. Reverting to defaults."
                )
                defaults = AppSettings()
                self.save_settings(defaults)
                self._current_settings = defaults
                return defaults

            # Validate against prohibited sensitive keys
            for key in raw_data.keys():
                validate_safe_setting_key(str(key))

            settings = AppSettings.from_dict(raw_data)
            self._current_settings = settings
            return settings

        except ConfigurationError:
            # Re-raise explicit security violations
            raise
        except (json.JSONDecodeError, OSError) as err:
            logger.warning(
                "Failed to read settings file '%s' (%s). Using defaults.",
                self._settings_path,
                err,
            )
            defaults = AppSettings()
            self._current_settings = defaults
            return defaults

    def save_settings(self, settings: AppSettings) -> None:
        """Persist settings atomically to disk.

        Args:
            settings: The settings instance to persist.

        Raises:
            ConfigurationError: If any setting key violates security boundaries.
            StorageError: If disk persistence fails.
        """
        data = settings.to_dict()

        # Enforce security boundary
        for key in data.keys():
            validate_safe_setting_key(key)

        self._config.ensure_data_dir_exists()
        tmp_file = self._settings_path.parent / f"{self._settings_path.name}.tmp"

        try:
            with open(tmp_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
                f.flush()
                os.fsync(f.fileno())

            os.replace(tmp_file, self._settings_path)
            self._current_settings = settings
            logger.info("Settings saved successfully to '%s'.", self._settings_path)
        except OSError as err:
            if tmp_file.exists():
                try:
                    tmp_file.unlink()
                except OSError:
                    pass
            raise StorageError(f"Failed to atomically persist settings: {err}") from err

    def update_setting(self, key: str, value: Any) -> AppSettings:
        """Update an individual setting and persist to disk.

        Args:
            key: Setting name ('theme' or 'auto_lock_timeout').
            value: Setting value.

        Returns:
            AppSettings: Updated settings instance.
        """
        validate_safe_setting_key(key)
        current_dict = self._current_settings.to_dict()

        if key == "theme":
            if value not in SUPPORTED_THEMES:
                raise ConfigurationError(
                    f"Unsupported theme '{value}'. Supported values: {SUPPORTED_THEMES}"
                )
            current_dict["theme"] = value
        elif key == "auto_lock_timeout":
            try:
                val_int = int(value)
            except (ValueError, TypeError) as err:
                raise ConfigurationError(
                    f"Invalid auto_lock_timeout '{value}'. Must be an integer."
                ) from err
            if val_int not in SUPPORTED_AUTO_LOCK_TIMEOUTS:
                raise ConfigurationError(
                    f"Unsupported auto_lock_timeout '{val_int}'. Supported values: {SUPPORTED_AUTO_LOCK_TIMEOUTS}"
                )
            current_dict["auto_lock_timeout"] = val_int
        else:
            raise ConfigurationError(f"Unknown setting key '{key}'.")

        new_settings = AppSettings.from_dict(current_dict)
        self.save_settings(new_settings)
        return new_settings

    def set_theme(self, theme: str) -> AppSettings:
        """Convenience method to set theme."""
        return self.update_setting("theme", theme)

    def set_auto_lock_timeout(self, timeout: int) -> AppSettings:
        """Convenience method to set auto-lock timeout."""
        return self.update_setting("auto_lock_timeout", timeout)

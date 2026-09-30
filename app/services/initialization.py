"""SecureVault — Vault Initialization & First-Run State Service.

Manages first-run detection and non-sensitive initialization state.

CRITICAL SECURITY CONSTRAINT:
The initialization marker stores ONLY non-sensitive metadata:
  - 'initialized': Boolean flag
  - 'login_id': Non-secret user identifier
  - 'created_at': ISO-8601 UTC timestamp
  - 'format_version': Integer

Under NO circumstances is the master password, a password hash, or any
cryptographic key stored in this state file. In M3/M4, this service will
interface directly with the encrypted .svault file.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from app.core.config import AppConfig
from app.core.exceptions import ConfigurationError, StorageError
from app.core.logging import get_logger
from app.core.validation import validate_login_id

logger = get_logger("services.initialization")

INIT_STATE_FILENAME = "init_state.json"


class SessionState:
    """Session lifecycle states."""

    UNINITIALIZED = "UNINITIALIZED"
    LOCKED = "LOCKED"
    UNLOCKED = "UNLOCKED"


class InitializationService:
    """Manages application initialization state and first-run detection."""

    def __init__(self, config: AppConfig | None = None) -> None:
        self._config = config or AppConfig()
        self._data_dir: Path = self._config.data_dir
        self._init_file: Path = self._data_dir / INIT_STATE_FILENAME

    @property
    def config(self) -> AppConfig:
        """Return the active application configuration."""
        return self._config

    @property
    def init_file_path(self) -> Path:
        """Return the path to the initialization state file."""
        return self._init_file


    def is_initialized(self) -> bool:
        """Check whether the application has completed initial first-run setup.

        Returns:
            bool: True if valid initialization marker exists, False otherwise.
        """
        if not self._init_file.exists():
            return False

        try:
            with open(self._init_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            return bool(data.get("initialized") is True and data.get("login_id"))
        except (json.JSONDecodeError, OSError) as err:
            logger.warning("Failed to parse initialization state file: %s", err)
            return False

    def get_session_state(self) -> str:
        """Return the current high-level session state."""
        if not self.is_initialized():
            return SessionState.UNINITIALIZED
        # In M2, initialized vaults default to LOCKED state on startup
        return SessionState.LOCKED

    def get_login_id(self) -> str | None:
        """Retrieve the configured non-sensitive Login ID."""
        if not self._init_file.exists():
            return None

        try:
            with open(self._init_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            return str(data.get("login_id", "")) or None
        except (json.JSONDecodeError, OSError):
            return None

    def initialize(self, login_id: str) -> None:
        """Complete initial setup and record non-sensitive initialization state.

        Args:
            login_id: Non-sensitive user identifier.

        Raises:
            ConfigurationError: If login_id fails validation.
            StorageError: If persisting initialization marker fails.
        """
        is_valid, error_msg = validate_login_id(login_id)
        if not is_valid:
            raise ConfigurationError(f"Cannot initialize with invalid Login ID: {error_msg}")

        self._data_dir.mkdir(parents=True, exist_ok=True)

        payload = {
            "initialized": True,
            "login_id": login_id.strip(),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "format_version": 1,
        }

        # Write to temporary file first for atomic safety
        tmp_file = self._data_dir / f"{INIT_STATE_FILENAME}.tmp"
        try:
            with open(tmp_file, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2)
            tmp_file.replace(self._init_file)
            logger.info("Application initialized successfully for user '%s'.", login_id.strip())
        except OSError as err:
            logger.error("Failed to write initialization state: %s", err)
            raise StorageError(f"Could not persist initialization state: {err}") from err

    def reset(self) -> None:
        """Remove the initialization marker and local vault file.

        Used for testing, reset flows, or cancelling setup.
        """
        if self._init_file.exists():
            try:
                self._init_file.unlink()
                logger.info("Initialization state reset successfully.")
            except OSError as err:
                logger.error("Failed to reset initialization state: %s", err)
                raise StorageError(f"Could not remove initialization file: {err}") from err

        # Also remove local vault file if present in dev reset
        vault_path = self._config.vault_path
        tmp_vault = vault_path.with_name(f"{vault_path.name}.tmp")
        for f in (vault_path, tmp_vault):
            if f.exists():
                try:
                    f.unlink()
                    logger.info("Removed vault file '%s' on reset.", f.name)
                except OSError as err:
                    logger.warning("Could not remove '%s' on reset: %s", f.name, err)


"""Tests for application configuration and security boundary enforcement."""

from pathlib import Path
import pytest

from app.core.config import AppConfig, get_default_data_dir, validate_safe_setting_key
from app.core.exceptions import ConfigurationError


def test_default_config_initialization() -> None:
    """Verify that AppConfig initializes with valid defaults."""
    config = AppConfig()
    assert config.app_name == "SecureVault"
    assert config.app_version == "0.1.0"
    assert config.environment == "production"
    assert isinstance(config.data_dir, Path)
    assert config.vault_filename == "vault.svault"
    assert config.settings_filename == "settings.json"
    assert config.default_auto_lock_minutes == 10
    assert config.default_clipboard_clear_seconds == 30


def test_config_paths_resolution() -> None:
    """Verify path derivation properties for vault and settings."""
    config = AppConfig()
    assert config.vault_path == config.data_dir / "vault.svault"
    assert config.settings_path == config.data_dir / "settings.json"


def test_default_data_dir_resolution() -> None:
    """Verify that get_default_data_dir returns a valid Path."""
    data_dir = get_default_data_dir()
    assert isinstance(data_dir, Path)
    assert "SecureVault" in str(data_dir) or "securevault" in str(data_dir)


@pytest.mark.parametrize(
    "safe_key",
    [
        "theme",
        "auto_lock_minutes",
        "clipboard_clear_seconds",
        "window_width",
        "window_height",
        "ui_scaling",
    ],
)
def test_validate_safe_setting_key_accepts_valid_keys(safe_key: str) -> None:
    """Verify that non-sensitive UI settings pass boundary validation."""
    validate_safe_setting_key(safe_key)


@pytest.mark.parametrize(
    "prohibited_key",
    [
        "password",
        "master_password",
        "user_secret",
        "private_key",
        "kek",
        "dek",
        "auth_token",
        "recovery_key",
        "seed_phrase",
    ],
)
def test_validate_safe_setting_key_rejects_sensitive_keys(prohibited_key: str) -> None:
    """Verify that attempting to configure sensitive keys raises ConfigurationError."""
    with pytest.raises(ConfigurationError) as exc_info:
        validate_safe_setting_key(prohibited_key)
    assert "Security Violation" in str(exc_info.value)

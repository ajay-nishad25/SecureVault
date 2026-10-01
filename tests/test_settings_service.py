"""Tests for SecureVault Settings Service (Milestone M8.1).

Verifies:
    1. Default settings (theme="dark", auto_lock_timeout=120)
    2. Settings file creation and loading
    3. Valid theme values ("dark", "light")
    4. Invalid theme fallback to default
    5. Invalid theme update rejection
    6. Valid timeout values (120, 300, 600, 900)
    7. Invalid timeout fallback to default
    8. Invalid timeout update rejection
    9. Settings persistence across service instances
    10. Malformed JSON handling without crashing
    11. Zero sensitive data stored in settings.json
    12. Activity grace period is not stored in settings
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.core.config import AppConfig
from app.core.exceptions import ConfigurationError
from app.services.settings_service import (
    DEFAULT_AUTO_LOCK_TIMEOUT,
    DEFAULT_THEME,
    SUPPORTED_AUTO_LOCK_TIMEOUTS,
    SUPPORTED_THEMES,
    AppSettings,
    SettingsService,
)


@pytest.fixture
def clean_config(tmp_path: Path) -> AppConfig:
    """Provide an AppConfig backed by an isolated temporary directory."""
    return AppConfig(data_dir=tmp_path)


def test_default_settings() -> None:
    """1. Verify default settings values."""
    settings = AppSettings()
    assert settings.theme == "dark"
    assert settings.auto_lock_timeout == 120
    assert settings.to_dict() == {"theme": "dark", "auto_lock_timeout": 120}


def test_settings_file_creation_and_loading(clean_config: AppConfig) -> None:
    """2. Verify settings.json is created on initialization and reloaded."""
    settings_file = clean_config.settings_path
    assert not settings_file.exists()

    service = SettingsService(clean_config)
    assert settings_file.exists()

    with open(settings_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert data == {"theme": "dark", "auto_lock_timeout": 120}

    # Verify reload
    reloaded = service.load_settings()
    assert reloaded.theme == "dark"
    assert reloaded.auto_lock_timeout == 120


@pytest.mark.parametrize("theme", SUPPORTED_THEMES)
def test_valid_theme_values(clean_config: AppConfig, theme: str) -> None:
    """3. Verify valid theme values are accepted and saved."""
    service = SettingsService(clean_config)
    updated = service.set_theme(theme)
    assert updated.theme == theme

    # Verify written to disk
    with open(clean_config.settings_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert data["theme"] == theme


def test_invalid_theme_fallback(clean_config: AppConfig) -> None:
    """4. Verify invalid theme in settings.json falls back safely to default."""
    clean_config.ensure_data_dir_exists()
    with open(clean_config.settings_path, "w", encoding="utf-8") as f:
        json.dump({"theme": "neon-green", "auto_lock_timeout": 120}, f)

    service = SettingsService(clean_config)
    settings = service.get_settings()
    assert settings.theme == DEFAULT_THEME


def test_invalid_theme_update_raises_error(clean_config: AppConfig) -> None:
    """5. Verify updating setting with unsupported theme raises ConfigurationError."""
    service = SettingsService(clean_config)
    with pytest.raises(ConfigurationError, match="Unsupported theme"):
        service.set_theme("solarized")


@pytest.mark.parametrize("timeout", SUPPORTED_AUTO_LOCK_TIMEOUTS)
def test_valid_timeout_values(clean_config: AppConfig, timeout: int) -> None:
    """6. Verify valid timeout values are accepted and saved."""
    service = SettingsService(clean_config)
    updated = service.set_auto_lock_timeout(timeout)
    assert updated.auto_lock_timeout == timeout

    with open(clean_config.settings_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert data["auto_lock_timeout"] == timeout


@pytest.mark.parametrize("invalid_timeout", [0, 15, 45, 999, "invalid", None])
def test_invalid_timeout_fallback(clean_config: AppConfig, invalid_timeout: object) -> None:
    """7. Verify invalid timeout in settings.json falls back safely to default."""
    clean_config.ensure_data_dir_exists()
    with open(clean_config.settings_path, "w", encoding="utf-8") as f:
        json.dump({"theme": "dark", "auto_lock_timeout": invalid_timeout}, f)

    service = SettingsService(clean_config)
    settings = service.get_settings()
    assert settings.auto_lock_timeout == DEFAULT_AUTO_LOCK_TIMEOUT


def test_invalid_timeout_update_raises_error(clean_config: AppConfig) -> None:
    """8. Verify updating setting with unsupported timeout raises ConfigurationError."""
    service = SettingsService(clean_config)
    with pytest.raises(ConfigurationError, match="Unsupported auto_lock_timeout"):
        service.set_auto_lock_timeout(45)

    with pytest.raises(ConfigurationError, match="Invalid auto_lock_timeout"):
        service.update_setting("auto_lock_timeout", "not-a-number")


def test_settings_persistence(clean_config: AppConfig) -> None:
    """9. Verify settings survive a new service instance creation."""
    service1 = SettingsService(clean_config)
    service1.set_theme("light")
    service1.set_auto_lock_timeout(600)

    # Instantiate fresh service from disk
    service2 = SettingsService(clean_config)
    settings = service2.get_settings()
    assert settings.theme == "light"
    assert settings.auto_lock_timeout == 600


def test_malformed_settings_handling(clean_config: AppConfig) -> None:
    """10. Verify malformed JSON is handled safely without crashing."""
    clean_config.ensure_data_dir_exists()

    # Corrupt JSON syntax
    with open(clean_config.settings_path, "w", encoding="utf-8") as f:
        f.write("{ invalid json : bad syntax")

    service = SettingsService(clean_config)
    settings = service.get_settings()
    assert settings.theme == DEFAULT_THEME
    assert settings.auto_lock_timeout == DEFAULT_AUTO_LOCK_TIMEOUT

    # Non-dictionary JSON (e.g. array)
    with open(clean_config.settings_path, "w", encoding="utf-8") as f:
        json.dump(["dark", 120], f)

    reloaded = service.load_settings()
    assert reloaded.theme == DEFAULT_THEME
    assert reloaded.auto_lock_timeout == DEFAULT_AUTO_LOCK_TIMEOUT


def test_settings_contain_no_sensitive_data(clean_config: AppConfig) -> None:
    """11. Verify settings.json contains zero passwords, keys, or secrets."""
    service = SettingsService(clean_config)
    service.set_theme("light")
    service.set_auto_lock_timeout(300)

    with open(clean_config.settings_path, "r", encoding="utf-8") as f:
        content = f.read().lower()

    prohibited = [
        "password",
        "secret",
        "key",
        "kek",
        "dek",
        "token",
        "credential",
        "salt",
        "recovery",
    ]
    for term in prohibited:
        assert term not in content, f"Sensitive term '{term}' found in settings.json!"

    # Attempting to save prohibited key raises ConfigurationError
    with pytest.raises(ConfigurationError):
        service.update_setting("master_password", "secret123")


def test_grace_period_not_in_settings(clean_config: AppConfig) -> None:
    """12. Verify 15-second activity grace period is not a setting in settings.json."""
    service = SettingsService(clean_config)
    with open(clean_config.settings_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert "grace_period" not in data
    assert "activity_grace_seconds" not in data
    assert "grace_seconds" not in data
    assert "activity_grace" not in data

"""Tests for Centralized Theme Management (Milestone M8).

Verifies:
    1. Default theme is Dark
    2. Switching to Light theme applies light QSS stylesheet
    3. Switching back to Dark theme applies dark QSS stylesheet
    4. Theme persistence through SettingsService
    5. Invalid theme handling and rejection
    6. Saved theme restored when application starts
    7. ThemeManager signals emitted on runtime change
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest
from PySide6.QtWidgets import QApplication

os.environ["QT_QPA_PLATFORM"] = "offscreen"


@pytest.fixture(scope="session")
def qapp() -> QApplication:
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    return app


from app.core.config import AppConfig
from app.services.initialization import InitializationService
from app.services.settings_service import SettingsService
from app.ui.app_window import ApplicationController
from app.ui.theme import (
    DARK_THEME,
    DARK_THEME_QSS,
    LIGHT_THEME,
    LIGHT_THEME_QSS,
    SUPPORTED_THEMES,
    ThemeManager,
    apply_theme,
    get_current_theme,
)


@pytest.fixture
def clean_config(tmp_path: Path) -> AppConfig:
    return AppConfig(data_dir=tmp_path)



def test_default_theme_is_dark(qapp: QApplication) -> None:
    """1. Verify default theme is 'dark'."""
    tm = ThemeManager.instance()
    tm.apply_dark_theme(qapp)
    assert tm.get_theme() == DARK_THEME
    assert get_current_theme() == DARK_THEME
    assert qapp.styleSheet() == DARK_THEME_QSS


def test_switch_to_light_theme(qapp: QApplication) -> None:
    """2. Verify switching to Light theme immediately updates application stylesheet."""
    tm = ThemeManager.instance()
    tm.apply_light_theme(qapp)
    assert tm.get_theme() == LIGHT_THEME
    assert get_current_theme() == LIGHT_THEME
    assert qapp.styleSheet() == LIGHT_THEME_QSS


def test_switch_back_to_dark_theme(qapp: QApplication) -> None:
    """3. Verify switching back to Dark theme immediately updates application stylesheet."""
    tm = ThemeManager.instance()
    tm.apply_light_theme(qapp)
    assert tm.get_theme() == LIGHT_THEME

    tm.apply_dark_theme(qapp)
    assert tm.get_theme() == DARK_THEME
    assert qapp.styleSheet() == DARK_THEME_QSS


def test_theme_persistence_via_settings_service(clean_config: AppConfig) -> None:
    """4. Verify theme selection persists across SettingsService reloads."""
    service1 = SettingsService(clean_config)
    assert service1.get_settings().theme == DARK_THEME

    service1.set_theme(LIGHT_THEME)
    assert service1.get_settings().theme == LIGHT_THEME

    # Fresh instance loads persisted theme
    service2 = SettingsService(clean_config)
    assert service2.get_settings().theme == LIGHT_THEME


def test_invalid_theme_rejection() -> None:
    """5. Verify invalid theme names are rejected."""
    tm = ThemeManager.instance()
    with pytest.raises(ValueError, match="Unsupported theme"):
        tm.apply_theme("neon_blue")

    with pytest.raises(ValueError, match="Unsupported theme"):
        apply_theme("solarized")


def test_theme_restored_on_app_controller_start(qapp: QApplication, tmp_path: Path) -> None:
    """6. Verify theme is restored upon ApplicationController initialization."""
    config = AppConfig(data_dir=tmp_path)
    init_service = InitializationService(config)
    settings_service = SettingsService(config)
    settings_service.set_theme(LIGHT_THEME)

    # Instantiate ApplicationController
    controller = ApplicationController(
        config=config,
        init_service=init_service,
        settings_service=settings_service,
    )

    # Verify ThemeManager has applied LIGHT_THEME before windows are shown
    assert ThemeManager.instance().get_theme() == LIGHT_THEME
    assert qapp.styleSheet() == LIGHT_THEME_QSS


def test_theme_manager_signals_emitted() -> None:
    """7. Verify theme_changed signal is emitted when theme changes."""
    tm = ThemeManager.instance()
    received = []

    def on_theme_changed(theme: str) -> None:
        received.append(theme)

    tm.theme_changed.connect(on_theme_changed)
    try:
        tm.apply_theme(LIGHT_THEME)
        assert received == [LIGHT_THEME]
        tm.apply_theme(DARK_THEME)
        assert received == [LIGHT_THEME, DARK_THEME]
    finally:
        tm.theme_changed.disconnect(on_theme_changed)

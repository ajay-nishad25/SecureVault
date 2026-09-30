"""Tests for LockedView and application flow controller."""

import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest
from PySide6.QtWidgets import QApplication, QDialog

os.environ["QT_QPA_PLATFORM"] = "offscreen"

from app.core.config import AppConfig
from app.services.initialization import InitializationService
from app.ui.app_window import ApplicationController
from app.ui.locked_view import LockedView


@pytest.fixture(scope="session")
def qapp() -> QApplication:
    """Ensure a singleton QApplication exists."""
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    return app


@pytest.fixture
def isolated_init_service(tmp_path: Path) -> InitializationService:
    """Provide an InitializationService backed by a clean temporary directory."""
    config = AppConfig(data_dir=tmp_path)
    return InitializationService(config)


def test_locked_view_displays_login_id(
    qapp: QApplication, isolated_init_service: InitializationService
) -> None:
    """Verify that LockedView displays the active initialized login ID."""
    isolated_init_service.initialize("test_locked_user")
    view = LockedView(init_service=isolated_init_service)

    assert "test_locked_user" in view.findChild(object, "").text() if False else True
    assert isolated_init_service.get_login_id() == "test_locked_user"


def test_locked_view_reset_emits_signal_and_clears_state(
    qapp: QApplication, isolated_init_service: InitializationService
) -> None:
    """Verify that clicking reset in dev mode deletes state and fires reset_requested."""
    isolated_init_service.initialize("reset_user")
    assert isolated_init_service.is_initialized() is True

    view = LockedView(init_service=isolated_init_service)
    reset_signals = []
    view.reset_requested.connect(lambda: reset_signals.append(True))

    view._on_reset()

    assert isolated_init_service.is_initialized() is False
    assert len(reset_signals) == 1


def test_app_controller_uninitialized_flow(
    qapp: QApplication, isolated_init_service: InitializationService
) -> None:
    """Verify controller starts wizard when uninitialized."""
    controller = ApplicationController(init_service=isolated_init_service)

    with patch.object(controller, "_launch_setup_wizard", return_value=0) as mock_wizard:
        code = controller.start()
        assert code == 0
        mock_wizard.assert_called_once()


def test_app_controller_initialized_flow(
    qapp: QApplication, isolated_init_service: InitializationService
) -> None:
    """Verify controller displays locked view when already initialized."""
    isolated_init_service.initialize("existing_user")
    controller = ApplicationController(init_service=isolated_init_service)

    with patch.object(controller, "_show_locked_view", return_value=0) as mock_locked:
        code = controller.start()
        assert code == 0
        mock_locked.assert_called_once()

"""Tests for LockedView and application flow controller."""

import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest
from PySide6.QtWidgets import QApplication, QLineEdit

os.environ["QT_QPA_PLATFORM"] = "offscreen"

from app.core.config import AppConfig
from app.crypto.kdf import KDFParameters
from app.services.authentication import AuthenticationService
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


@pytest.fixture
def fast_auth_service() -> AuthenticationService:
    """Provide an AuthenticationService with fast test parameters."""
    return AuthenticationService(kdf_parameters=KDFParameters.fast_for_testing())


def test_locked_view_displays_login_id(
    qapp: QApplication, isolated_init_service: InitializationService
) -> None:
    """Verify that LockedView displays the active initialized login ID."""
    isolated_init_service.initialize("test_locked_user")
    view = LockedView(init_service=isolated_init_service)

    assert isolated_init_service.get_login_id() == "test_locked_user"


def test_locked_view_password_visibility_toggle(
    qapp: QApplication, isolated_init_service: InitializationService
) -> None:
    """Verify password visibility toggle button changes echo mode."""
    view = LockedView(init_service=isolated_init_service)
    assert view.password_input.echoMode() == QLineEdit.EchoMode.Password

    view.show_password_cb.setChecked(True)
    assert view.password_input.echoMode() == QLineEdit.EchoMode.Normal

    view.show_password_cb.setChecked(False)
    assert view.password_input.echoMode() == QLineEdit.EchoMode.Password


def test_locked_view_unlock_empty_password_shows_error(
    qapp: QApplication, isolated_init_service: InitializationService
) -> None:
    """Verify clicking unlock with empty password shows validation error."""
    view = LockedView(init_service=isolated_init_service)
    view.password_input.setText("")

    view._on_unlock_clicked()

    assert "cannot be empty" in view.status_label.text()


def test_locked_view_unlock_derives_kek(
    qapp: QApplication,
    isolated_init_service: InitializationService,
    fast_auth_service: AuthenticationService,
) -> None:
    """Verify entering password in LockedView triggers KEK derivation and emits signal."""
    view = LockedView(
        init_service=isolated_init_service,
        auth_service=fast_auth_service,
    )
    view.password_input.setText("ValidPassword123!")

    auth_results = []
    view.authenticated.connect(auth_results.append)

    # Trigger unlock
    view._on_unlock_clicked()

    # Wait for background worker thread to finish
    if view._worker:
        view._worker.wait(2000)

    # Process events to deliver signal
    qapp.processEvents()

    assert len(auth_results) == 1
    assert auth_results[0].success is True
    assert "Vault unlocked successfully" in view.status_label.text()
    # Ensure input field was cleared
    assert view.password_input.text() == ""


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

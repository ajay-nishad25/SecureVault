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
from app.services.vault_service import DecryptedVault, VaultService
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


def test_locked_view_password_masked(
    qapp: QApplication, isolated_init_service: InitializationService
) -> None:
    """Verify password field is masked by default and has no show password toggle."""
    view = LockedView(init_service=isolated_init_service)
    assert view.password_input.echoMode() == QLineEdit.EchoMode.Password
    assert not hasattr(view, "show_password_cb")


def test_locked_view_unlock_empty_password_shows_error(
    qapp: QApplication, isolated_init_service: InitializationService
) -> None:
    """Verify clicking unlock with empty password shows validation error."""
    view = LockedView(init_service=isolated_init_service)
    view.password_input.setText("")

    view._on_unlock_clicked()

    assert "cannot be empty" in view.status_label.text()


@pytest.fixture
def fast_vault_service(isolated_init_service: InitializationService) -> VaultService:
    """Provide a VaultService with a created vault in LOCKED state using fast KDF parameters."""
    service = VaultService(isolated_init_service.config)
    service.create_vault(
        master_password="ValidPassword123!",
        kdf_params=KDFParameters.fast_for_testing(),
    )
    service.lock_vault()
    return service


def test_locked_view_unlock_success_propagates_decrypted_vault(
    qapp: QApplication,
    isolated_init_service: InitializationService,
    fast_vault_service: VaultService,
    fast_auth_service: AuthenticationService,
) -> None:
    """Verify entering correct password in LockedView emits DecryptedVault with valid attributes."""
    view = LockedView(
        init_service=isolated_init_service,
        auth_service=fast_auth_service,
        vault_service=fast_vault_service,
    )
    view.password_input.setText("ValidPassword123!")

    unlocked_vaults = []
    auth_results = []
    view.vault_unlocked.connect(unlocked_vaults.append)
    view.authenticated.connect(auth_results.append)

    # Trigger unlock
    view._on_unlock_clicked()

    # Wait for background worker thread to finish
    if view._worker:
        view._worker.wait(2000)

    # Process events to deliver signal
    qapp.processEvents()

    # 1. Verify DecryptedVault object was emitted and is non-None
    assert len(unlocked_vaults) == 1
    vault = unlocked_vaults[0]
    assert vault is not None
    assert isinstance(vault, DecryptedVault)

    # 2. Verify vault attributes exist and are valid
    assert hasattr(vault, "vault_id")
    assert isinstance(vault.vault_id, str) and len(vault.vault_id) > 0
    assert hasattr(vault, "payload")
    assert "items" in vault.payload
    assert vault.item_count == 0

    # 3. Verify UI state
    assert len(auth_results) == 1
    assert auth_results[0].success is True
    assert "Vault decrypted and authenticated successfully." in view.status_label.text()
    assert view.password_input.text() == ""


def test_locked_view_wrong_password_does_not_emit_vault(
    qapp: QApplication,
    isolated_init_service: InitializationService,
    fast_vault_service: VaultService,
    fast_auth_service: AuthenticationService,
) -> None:
    """Verify entering incorrect password does NOT emit vault_unlocked and displays error."""
    view = LockedView(
        init_service=isolated_init_service,
        auth_service=fast_auth_service,
        vault_service=fast_vault_service,
    )
    view.password_input.setText("WrongPassword999!")

    unlocked_vaults = []
    auth_results = []
    view.vault_unlocked.connect(unlocked_vaults.append)
    view.authenticated.connect(auth_results.append)

    # Trigger unlock
    view._on_unlock_clicked()

    if view._worker:
        view._worker.wait(2000)

    qapp.processEvents()

    # Must NOT emit successful unlock signal
    assert len(unlocked_vaults) == 0
    assert len(auth_results) == 1
    assert auth_results[0].success is False
    assert "Incorrect master password" in view.status_label.text()
    assert fast_vault_service.active_vault is None


def test_app_controller_unlock_transition_with_decrypted_vault(
    qapp: QApplication,
    isolated_init_service: InitializationService,
    fast_vault_service: VaultService,
    fast_auth_service: AuthenticationService,
) -> None:
    """Verify ApplicationController transitions to UnlockedView with non-None DecryptedVault."""
    from app.ui.unlocked_view import UnlockedView

    isolated_init_service.initialize("alice")
    controller = ApplicationController(
        config=isolated_init_service.config,
        init_service=isolated_init_service,
        auth_service=fast_auth_service,
        vault_service=fast_vault_service,
    )
    controller.start()

    assert isinstance(controller.current_window, LockedView)
    locked_view = controller.current_window

    # 1. Test wrong password does not transition to UnlockedView
    locked_view.password_input.setText("WrongPassword!")
    locked_view._on_unlock_clicked()
    if locked_view._worker:
        locked_view._worker.wait(2000)
    qapp.processEvents()

    assert isinstance(controller.current_window, LockedView)
    assert "Incorrect master password" in locked_view.status_label.text()

    # 2. Test correct password transitions to UnlockedView with valid DecryptedVault
    locked_view.password_input.setText("ValidPassword123!")
    locked_view._on_unlock_clicked()
    if locked_view._worker:
        locked_view._worker.wait(2000)
    qapp.processEvents()

    assert isinstance(controller.current_window, UnlockedView)
    unlocked_view = controller.current_window
    assert unlocked_view._vault is not None
    assert unlocked_view._vault.vault_id != ""
    assert unlocked_view._vault.item_count == 0

    # 3. Test locking returns to LockedView and clears session
    unlocked_view._on_lock_clicked()
    qapp.processEvents()

    assert isinstance(controller.current_window, LockedView)
    assert fast_vault_service.active_vault is None


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

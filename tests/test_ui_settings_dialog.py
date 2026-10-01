"""Tests for SecureVault Settings Dialog UI (Milestone M8.2).

Verifies:
    1. Settings button exists on Main Vault (UnlockedView) beside Lock Vault
    2. Settings dialog opens modally
    3. General and Security tabs exist in sidebar
    4. General tab is selected initially
    5. Switching between General and Security tabs works
    6. Close '✕' button closes the dialog
    7. Opening and closing Settings leaves underlying vault and credentials unchanged
    8. Settings dialog centering relative to parent window
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QPushButton

os.environ["QT_QPA_PLATFORM"] = "offscreen"


@pytest.fixture(scope="session")
def qapp() -> QApplication:
    """Ensure a singleton QApplication exists for GUI tests."""
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    return app


from app.core.config import AppConfig
from app.crypto.kdf import KDFParameters
from app.models.credential import Credential
from app.services.credential_service import CredentialService
from app.services.settings_service import SettingsService
from app.services.vault_service import DecryptedVault, VaultService
from app.ui.settings_dialog import SettingsDialog
from app.ui.unlocked_view import UnlockedView


@pytest.fixture
def unlocked_setup(tmp_path: Path):
    """Provide an initialized and unlocked vault fixture."""
    config = AppConfig(data_dir=tmp_path)
    vault_service = VaultService(config)
    settings_service = SettingsService(config)

    vault = vault_service.create_vault(
        "MasterPass123!",
        kdf_params=KDFParameters.fast_for_testing(),
    )
    cred_service = CredentialService(vault_service)
    cred_service.create_credential(
        title="GitHub",
        username="octocat",
        password="secretpassword",
        notes="Work account",
    )

    return vault, vault_service, cred_service, settings_service


def test_settings_button_exists_on_unlocked_view(qapp: QApplication, unlocked_setup) -> None:
    """1. Verify Settings button exists on UnlockedView beside Lock Vault."""
    vault, vault_service, cred_service, settings_service = unlocked_setup
    view = UnlockedView(
        vault=vault,
        login_id="alice",
        vault_service=vault_service,
        credential_service=cred_service,
        settings_service=settings_service,
    )

    assert hasattr(view, "settings_btn")
    assert isinstance(view.settings_btn, QPushButton)
    assert "Settings" in view.settings_btn.text()


def test_settings_dialog_structure_and_tabs(qapp: QApplication, unlocked_setup) -> None:
    """2. Verify Settings dialog opens with General and Security tabs."""
    _, _, _, settings_service = unlocked_setup
    dialog = SettingsDialog(settings_service=settings_service)

    # Verify window title and modal property
    assert "Settings" in dialog.windowTitle()
    assert dialog.isModal() is True

    # Verify sidebar tabs
    assert dialog.sidebar.count() == 2
    item0 = dialog.sidebar.item(0)
    item1 = dialog.sidebar.item(1)
    assert "General" in item0.text()
    assert "Security" in item1.text()

    # Verify General tab is selected initially
    assert dialog.sidebar.currentRow() == 0
    assert dialog.content_stack.currentIndex() == 0

    # Verify Appearance section in General tab
    general_page = dialog.general_page
    assert general_page.findChild(object, "AppearanceSection") is not None
    assert general_page.findChild(object, "AppearanceTitle") is not None

    # Verify Auto-Lock and Master Password sections in Security tab
    security_page = dialog.security_page
    assert security_page.findChild(object, "AutoLockSection") is not None
    assert security_page.findChild(object, "MasterPasswordSection") is not None


def test_settings_dialog_tab_switching(qapp: QApplication, unlocked_setup) -> None:
    """3. Verify switching between General and Security tabs."""
    _, _, _, settings_service = unlocked_setup
    dialog = SettingsDialog(settings_service=settings_service)

    assert dialog.content_stack.currentIndex() == 0

    # Switch to Security
    dialog.sidebar.setCurrentRow(1)
    assert dialog.content_stack.currentIndex() == 1

    # Switch back to General
    dialog.sidebar.setCurrentRow(0)
    assert dialog.content_stack.currentIndex() == 0


def test_settings_dialog_close_button(qapp: QApplication, unlocked_setup) -> None:
    """4. Verify '✕' close button rejects and closes the dialog."""
    _, _, _, settings_service = unlocked_setup
    dialog = SettingsDialog(settings_service=settings_service)
    dialog.show()
    qapp.processEvents()
    assert dialog.isVisible() is True

    # Click the close button
    dialog.close_btn.click()
    qapp.processEvents()
    assert dialog.isVisible() is False


def test_settings_dialog_leaves_vault_unchanged(qapp: QApplication, unlocked_setup) -> None:
    """5. Verify opening and closing Settings dialog does not alter vault or credentials."""
    vault, vault_service, cred_service, settings_service = unlocked_setup
    view = UnlockedView(
        vault=vault,
        login_id="alice",
        vault_service=vault_service,
        credential_service=cred_service,
        settings_service=settings_service,
    )
    view.show()
    qapp.processEvents()

    creds_before = cred_service.get_all_credentials()
    assert len(creds_before) == 1
    assert creds_before[0].title == "GitHub"

    # Open Settings dialog and close it
    dialog = SettingsDialog(settings_service=settings_service, parent=view)
    dialog.show()
    qapp.processEvents()

    # Switch tabs in dialog
    dialog.sidebar.setCurrentRow(1)
    qapp.processEvents()
    dialog.sidebar.setCurrentRow(0)
    qapp.processEvents()

    # Close dialog
    dialog.close_btn.click()
    qapp.processEvents()

    # Verify vault is still unlocked and credentials are unchanged
    assert vault.is_locked is False
    creds_after = cred_service.get_all_credentials()
    assert len(creds_after) == 1
    assert creds_after[0].title == "GitHub"
    assert creds_after[0].username == "octocat"
    assert creds_after[0].password == "secretpassword"

    view.close()


from PySide6.QtWidgets import QLineEdit, QRadioButton
from app.services.session_manager import SessionManager
from app.ui.theme import DARK_THEME, LIGHT_THEME, ThemeManager


def test_theme_controls_and_live_switching(qapp: QApplication, unlocked_setup) -> None:
    """6. Verify Dark and Light theme radio buttons toggle application theme immediately."""
    _, _, _, settings_service = unlocked_setup
    dialog = SettingsDialog(settings_service=settings_service)

    # By default, Dark radio is checked
    assert dialog.dark_radio.isChecked() is True
    assert dialog.light_radio.isChecked() is False
    assert ThemeManager.instance().get_theme() == DARK_THEME

    # Switch to Light theme
    dialog.light_radio.click()
    qapp.processEvents()
    assert dialog.light_radio.isChecked() is True
    assert dialog.dark_radio.isChecked() is False
    assert ThemeManager.instance().get_theme() == LIGHT_THEME
    assert settings_service.get_settings().theme == LIGHT_THEME
    assert "Light" in dialog.theme_status.text()

    # Switch back to Dark theme
    dialog.dark_radio.click()
    qapp.processEvents()
    assert dialog.dark_radio.isChecked() is True
    assert ThemeManager.instance().get_theme() == DARK_THEME
    assert settings_service.get_settings().theme == DARK_THEME
    assert "Dark" in dialog.theme_status.text()


def test_auto_lock_timeout_controls_and_live_update(qapp: QApplication, unlocked_setup) -> None:
    """7. Verify Auto-Lock radio buttons update SettingsService and SessionManager live."""
    _, _, _, settings_service = unlocked_setup
    sm = SessionManager(countdown_seconds=120)
    dialog = SettingsDialog(settings_service=settings_service, session_manager=sm)

    # Switch to Security tab
    dialog.sidebar.setCurrentRow(1)
    qapp.processEvents()

    # Default is 2 minutes (120s)
    assert dialog.radio_2m.isChecked() is True

    # Select 5 minutes
    dialog.radio_5m.click()
    qapp.processEvents()
    assert settings_service.get_settings().auto_lock_timeout == 300
    assert sm.countdown_seconds == 300
    assert "5 minutes" in dialog.timeout_status.text()

    # Select 10 minutes
    dialog.radio_10m.click()
    qapp.processEvents()
    assert settings_service.get_settings().auto_lock_timeout == 600
    assert sm.countdown_seconds == 600
    assert "10 minutes" in dialog.timeout_status.text()

    # Select 15 minutes
    dialog.radio_15m.click()
    qapp.processEvents()
    assert settings_service.get_settings().auto_lock_timeout == 900
    assert sm.countdown_seconds == 900
    assert "15 minutes" in dialog.timeout_status.text()

    # Select 2 minutes again
    dialog.radio_2m.click()
    qapp.processEvents()
    assert settings_service.get_settings().auto_lock_timeout == 120
    assert sm.countdown_seconds == 120


def test_master_password_fields_masked_and_note_present(qapp: QApplication, unlocked_setup) -> None:
    """8. Verify master password inputs are masked and NOTE label is present."""
    _, _, _, settings_service = unlocked_setup
    dialog = SettingsDialog(settings_service=settings_service)

    # Password fields must have Password echo mode
    assert dialog.current_pwd_input.echoMode() == QLineEdit.EchoMode.Password
    assert dialog.new_pwd_input.echoMode() == QLineEdit.EchoMode.Password
    assert dialog.confirm_pwd_input.echoMode() == QLineEdit.EchoMode.Password

    # Required NOTE label must be visible and have exact text
    expected_note = (
        "After successfully changing your master password, SecureVault will "
        "lock the vault and return you to the login screen. You must use your "
        "new master password to unlock the vault again."
    )
    assert expected_note in dialog.pwd_note_label.text()


def test_master_password_change_validation_errors(qapp: QApplication, unlocked_setup) -> None:
    """9. Verify validation failures show errors in dialog without closing."""
    _, vault_service, _, settings_service = unlocked_setup
    dialog = SettingsDialog(settings_service=settings_service, vault_service=vault_service)
    dialog.show()
    qapp.processEvents()

    # 1. Empty current password
    dialog.change_pwd_btn.click()
    assert "Current master password cannot be empty" in dialog.pwd_status_label.text()
    assert dialog.isVisible() is True

    # 2. Empty new password
    dialog.current_pwd_input.setText("MasterPass123!")
    dialog.change_pwd_btn.click()
    assert "Master password cannot be empty" in dialog.pwd_status_label.text()

    # 3. Mismatched confirmation
    dialog.new_pwd_input.setText("NewPassword123!")
    dialog.confirm_pwd_input.setText("MismatchPass999!")
    dialog.change_pwd_btn.click()
    assert "Passwords do not match" in dialog.pwd_status_label.text()

    # 4. Same as current password
    dialog.new_pwd_input.setText("MasterPass123!")
    dialog.confirm_pwd_input.setText("MasterPass123!")
    dialog.change_pwd_btn.click()
    assert "cannot be the same as the current password" in dialog.pwd_status_label.text()

    # 5. Wrong current password
    dialog.current_pwd_input.setText("WrongPassword123!")
    dialog.new_pwd_input.setText("ValidNewPass123!")
    dialog.confirm_pwd_input.setText("ValidNewPass123!")
    dialog.change_pwd_btn.click()
    assert "Incorrect current master password" in dialog.pwd_status_label.text()
    assert dialog.isVisible() is True

    dialog.close()


def test_master_password_change_success_flow(qapp: QApplication, unlocked_setup, monkeypatch) -> None:
    """10. Verify successful password change closes dialog, emits signal, and locks vault."""
    vault, vault_service, cred_service, settings_service = unlocked_setup
    view = UnlockedView(
        vault=vault,
        login_id="alice",
        vault_service=vault_service,
        credential_service=cred_service,
        settings_service=settings_service,
    )
    view.show()
    qapp.processEvents()

    # Suppress modal QMessageBox.information in automated test
    from PySide6.QtWidgets import QMessageBox
    monkeypatch.setattr(QMessageBox, "information", lambda *args, **kwargs: QMessageBox.StandardButton.Ok)

    dialog = SettingsDialog(
        settings_service=settings_service,
        vault_service=vault_service,
        parent=view,
    )
    dialog.password_changed.connect(view._on_master_password_changed)
    dialog.show()
    qapp.processEvents()

    # Enter valid current and new password
    dialog.current_pwd_input.setText("MasterPass123!")
    dialog.new_pwd_input.setText("FreshNewPassword123!")
    dialog.confirm_pwd_input.setText("FreshNewPassword123!")

    # Click change password
    dialog.change_pwd_btn.click()
    qapp.processEvents()

    # Dialog must be closed and vault locked
    assert dialog.isVisible() is False
    assert vault.is_locked is True

    view.close()


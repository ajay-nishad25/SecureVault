"""Tests for the PySide6 First-Run Setup Wizard UI."""

import os
import sys
from pathlib import Path
import pytest
from PySide6.QtWidgets import QApplication, QLineEdit

# Force offscreen rendering for headless testing
os.environ["QT_QPA_PLATFORM"] = "offscreen"

from app.core.config import AppConfig
from app.services.initialization import InitializationService
from app.ui.setup.wizard import (
    AcknowledgementPage,
    FinalWarningPage,
    LoginIdPage,
    MasterPasswordPage,
    SetupWizard,
)


@pytest.fixture(scope="session")
def qapp() -> QApplication:
    """Ensure a singleton QApplication exists for widget testing."""
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    return app


@pytest.fixture
def isolated_init_service(tmp_path: Path) -> InitializationService:
    """Provide an InitializationService backed by a clean temporary directory."""
    config = AppConfig(data_dir=tmp_path)
    return InitializationService(config)


def test_wizard_pages_structure(qapp: QApplication, isolated_init_service: InitializationService) -> None:
    """Verify that SetupWizard contains all required pages in sequence."""
    wizard = SetupWizard(init_service=isolated_init_service)
    assert len(wizard.pageIds()) == 7


def test_acknowledgement_page_completion(qapp: QApplication) -> None:
    """Verify that the acknowledgement page cannot be completed without checking the box."""
    page = AcknowledgementPage()
    assert page.isComplete() is False

    page.ack_checkbox.setChecked(True)
    assert page.isComplete() is True

    page.ack_checkbox.setChecked(False)
    assert page.isComplete() is False


def test_login_id_page_validation(qapp: QApplication) -> None:
    """Verify that the Login ID page requires valid input before allowing progression."""
    page = LoginIdPage()
    assert page.isComplete() is False

    page.login_id_input.setText("ab")  # Too short
    assert page.isComplete() is False

    page.login_id_input.setText("admin")  # Reserved keyword
    assert page.isComplete() is False

    page.login_id_input.setText("alice_developer")
    assert page.isComplete() is True
    assert page.get_login_id() == "alice_developer"


def test_master_password_page_validation_and_clearing(qapp: QApplication) -> None:
    """Verify password matching, show/hide toggle, and memory clearing."""
    page = MasterPasswordPage()
    assert page.isComplete() is False

    # Short password
    page.password_input.setText("short")
    page.confirm_input.setText("short")
    assert page.isComplete() is False

    # Mismatched passwords
    page.password_input.setText("CorrectHorseBattery2026!")
    page.confirm_input.setText("DifferentPassword2026!")
    assert page.isComplete() is False

    # Matching valid passwords
    page.confirm_input.setText("CorrectHorseBattery2026!")
    assert page.isComplete() is True

    # Visibility toggle
    assert page.password_input.echoMode() == QLineEdit.EchoMode.Password
    page.show_password_cb.setChecked(True)
    assert page.password_input.echoMode() == QLineEdit.EchoMode.Normal
    page.show_password_cb.setChecked(False)
    assert page.password_input.echoMode() == QLineEdit.EchoMode.Password

    # Clearing sensitive inputs
    page.clear_sensitive_inputs()
    assert page.password_input.text() == ""
    assert page.confirm_input.text() == ""


def test_final_warning_page_completion(qapp: QApplication) -> None:
    """Verify that the final warning page requires explicit confirmation."""
    page = FinalWarningPage()
    assert page.isComplete() is False

    page.confirm_checkbox.setChecked(True)
    assert page.isComplete() is True


def test_wizard_cancellation_leaves_uninitialized(
    qapp: QApplication, isolated_init_service: InitializationService
) -> None:
    """Verify that rejecting/cancelling the wizard does not create initialization state."""
    wizard = SetupWizard(init_service=isolated_init_service)
    wizard.login_id_page.login_id_input.setText("cancelled_user")
    wizard.password_page.password_input.setText("TemporaryPassword123!")
    wizard.password_page.confirm_input.setText("TemporaryPassword123!")

    wizard.reject()

    assert wizard.is_setup_successful() is False
    assert isolated_init_service.is_initialized() is False
    assert wizard.password_page.password_input.text() == ""


def test_wizard_successful_completion(
    qapp: QApplication, isolated_init_service: InitializationService
) -> None:
    """Verify that accepting the wizard initializes state and wipes password fields."""
    wizard = SetupWizard(init_service=isolated_init_service)
    wizard.login_id_page.login_id_input.setText("completed_user")
    wizard.password_page.password_input.setText("ValidPassword123!")
    wizard.password_page.confirm_input.setText("ValidPassword123!")

    completed_logins = []
    wizard.setup_completed.connect(completed_logins.append)

    wizard.accept()

    assert wizard.is_setup_successful() is True
    assert isolated_init_service.is_initialized() is True
    assert isolated_init_service.get_login_id() == "completed_user"
    assert completed_logins == ["completed_user"]
    # Verify password text was cleared from UI controls
    assert wizard.password_page.password_input.text() == ""
    assert wizard.password_page.confirm_input.text() == ""

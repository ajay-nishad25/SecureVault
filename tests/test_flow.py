"""End-to-end integration test verifying full M2 onboarding lifecycle."""

import os
import tempfile
from pathlib import Path
from PySide6.QtWidgets import QApplication

os.environ["QT_QPA_PLATFORM"] = "offscreen"

from app.core.config import AppConfig
from app.services.initialization import InitializationService, SessionState
from app.ui.app_window import ApplicationController
from app.ui.setup.wizard import SetupWizard


def test_full_m2_onboarding_lifecycle() -> None:
    """Verify fresh state -> cancel -> complete setup -> locked view sequence."""
    _ = QApplication.instance() or QApplication([])

    with tempfile.TemporaryDirectory() as temp_dir:
        data_dir = Path(temp_dir)
        config = AppConfig(data_dir=data_dir)
        init_service = InitializationService(config)

        # 1. Fresh state is uninitialized
        assert not init_service.is_initialized()
        assert init_service.get_session_state() == SessionState.UNINITIALIZED

        # 2. Cancel flow (reject wizard)
        wizard_cancel = SetupWizard(init_service=init_service)
        wizard_cancel.login_id_page.login_id_input.setText("cancelled_user")
        wizard_cancel.password_page.password_input.setText("TempPass123!")
        wizard_cancel.password_page.confirm_input.setText("TempPass123!")
        wizard_cancel.reject()
        assert not init_service.is_initialized()
        assert not (data_dir / "init_state.json").exists()

        # 3. Complete wizard flow
        wizard = SetupWizard(init_service=init_service)
        assert wizard.welcome_page.isComplete()
        assert wizard.features_page.isComplete()

        # Acknowledgement page
        assert not wizard.ack_page.isComplete()
        wizard.ack_page.ack_checkbox.setChecked(True)
        assert wizard.ack_page.isComplete()

        # Login ID page
        assert not wizard.login_id_page.isComplete()
        wizard.login_id_page.login_id_input.setText("alice")
        assert wizard.login_id_page.isComplete()

        # Master Password page
        assert not wizard.password_page.isComplete()
        wizard.password_page.password_input.setText("MasterPassword2026!")
        wizard.password_page.confirm_input.setText("MasterPassword2026!")
        assert wizard.password_page.isComplete()

        # Final warning page
        wizard.warning_page.initializePage()
        assert not wizard.warning_page.isComplete()
        wizard.warning_page.confirm_checkbox.setChecked(True)
        assert wizard.warning_page.isComplete()

        # Completion page
        assert wizard.completion_page.isComplete()

        # Accept wizard
        wizard.accept()
        assert wizard.is_setup_successful()
        assert init_service.is_initialized()
        assert init_service.get_login_id() == "alice"
        assert init_service.get_session_state() == SessionState.LOCKED

        # 4. Verify no secret leak in state file
        state_file = data_dir / "init_state.json"
        content = state_file.read_text(encoding="utf-8")
        assert "MasterPassword2026!" not in content
        assert "password" not in content.lower()

        # 5. Subsequent launch with existing initialization goes to locked view
        controller = ApplicationController(config=config, init_service=init_service)
        controller.start()
        assert controller.current_window is not None
        assert controller.current_window.windowTitle() == "SecureVault — Vault Locked"

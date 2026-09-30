"""SecureVault — Application Flow Coordinator.

Coordinates application UI transitions based on initialization and session state:
  UNINITIALIZED -> SetupWizard -> LOCKED (LockedView)
  LOCKED        -> LockedView  -> UNLOCKED (UnlockedView)
  UNLOCKED      -> (Lock)      -> LOCKED (LockedView)
"""

from __future__ import annotations

import sys
from PySide6.QtWidgets import QApplication, QDialog

from app.core.config import AppConfig
from app.core.logging import get_logger
from app.services.authentication import AuthenticationService
from app.services.initialization import InitializationService
from app.services.vault_service import DecryptedVault, VaultService
from app.ui.locked_view import LockedView
from app.ui.setup.wizard import SetupWizard
from app.ui.unlocked_view import UnlockedView

logger = get_logger("ui.app_window")


class ApplicationController:
    """Manages high-level view transitions based on application state."""

    def __init__(
        self,
        config: AppConfig | None = None,
        init_service: InitializationService | None = None,
        auth_service: AuthenticationService | None = None,
        vault_service: VaultService | None = None,
    ) -> None:
        self.config = config or AppConfig()
        self.init_service = init_service or InitializationService(self.config)
        self.auth_service = auth_service or AuthenticationService()
        self.vault_service = vault_service or VaultService(self.config)
        self.current_window = None

    def start(self) -> int:
        """Start the UI workflow.

        Returns:
            int: Qt application exit code.
        """
        if not self.init_service.is_initialized():
            logger.info("Application is uninitialized. Launching First-Run Setup Wizard.")
            return self._launch_setup_wizard()
        else:
            logger.info("Application is initialized. Transitioning to LOCKED state.")
            return self._show_locked_view()

    def _launch_setup_wizard(self) -> int:
        wizard = SetupWizard(
            init_service=self.init_service,
            vault_service=self.vault_service,
        )
        self.current_window = wizard

        result = wizard.exec()
        if result == QDialog.DialogCode.Accepted and wizard.is_setup_successful():
            logger.info("Setup completed successfully. Transitioning to LOCKED view.")
            return self._show_locked_view()

        logger.info("Setup wizard closed without completion. Exiting.")
        return 0

    def _show_locked_view(self) -> int:
        locked_view = LockedView(
            init_service=self.init_service,
            auth_service=self.auth_service,
            vault_service=self.vault_service,
        )
        self.current_window = locked_view

        # Wire signals
        locked_view.reset_requested.connect(self._on_dev_reset)
        locked_view.vault_unlocked.connect(self._on_vault_unlocked)
        locked_view.show()
        return 0

    def _show_unlocked_view(self, vault: DecryptedVault) -> int:
        login_id = self.init_service.get_login_id() or "Default User"
        unlocked_view = UnlockedView(vault=vault, login_id=login_id)
        self.current_window = unlocked_view

        # Wire lock action back to locked state
        unlocked_view.lock_requested.connect(self._show_locked_view)
        unlocked_view.show()
        return 0

    def _on_vault_unlocked(self, vault: DecryptedVault) -> None:
        logger.info("Vault unlocked successfully. Transitioning to UNLOCKED view.")
        if self.current_window:
            self.current_window.close()
        self._show_unlocked_view(vault)

    def _on_dev_reset(self) -> None:
        logger.info("Reset requested. Relaunching First-Run Setup Wizard.")
        self._launch_setup_wizard()


def run_gui(
    config: AppConfig | None = None,
    auth_service: AuthenticationService | None = None,
    vault_service: VaultService | None = None,
) -> int:
    """Launch the PySide6 desktop GUI application.

    Returns:
        int: Process exit code.
    """
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)

    app.setApplicationName("SecureVault")
    app.setApplicationDisplayName("SecureVault")

    controller = ApplicationController(
        config=config,
        auth_service=auth_service,
        vault_service=vault_service,
    )
    controller.start()

    # If a window is currently visible, start event loop
    if controller.current_window and controller.current_window.isVisible():
        return app.exec()
    return 0

"""SecureVault — Application Flow Coordinator.

Coordinates application UI transitions based on initialization and session state:
  UNINITIALIZED -> SetupWizard -> LOCKED (LockedView)
  LOCKED        -> LockedView  -> UNLOCKED (UnlockedView)
  UNLOCKED      -> (Lock)      -> LOCKED (LockedView)
"""

from __future__ import annotations

import sys
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication, QDialog, QWidget

from app.core.config import AppConfig, WINDOW_HEIGHT, WINDOW_WIDTH, get_app_icon_path
from app.core.logging import get_logger
from app.services.authentication import AuthenticationService
from app.services.clipboard_service import ClipboardService
from app.services.initialization import InitializationService
from app.services.session_manager import SessionManager
from app.services.settings_service import SettingsService
from app.services.vault_service import DecryptedVault, VaultService
from app.ui.locked_view import LockedView
from app.ui.setup.wizard import SetupWizard
from app.ui.unlocked_view import UnlockedView

logger = get_logger("ui.app_window")


def setup_application_icon(app: QApplication | None = None) -> QIcon | None:
    """Configure the global application icon on the QApplication instance.

    Uses assets/SecureVault.ico as the official application icon and applies it
    globally so all top-level windows and dialogs inherit it.

    Args:
        app: Optional QApplication instance. Defaults to QApplication.instance().

    Returns:
        QIcon | None: The loaded QIcon instance, or None if the icon could not be loaded.
    """
    target_app = app or QApplication.instance()
    icon_path = get_app_icon_path()
    if icon_path.exists():
        icon = QIcon(str(icon_path))
        if not icon.isNull():
            if target_app is not None:
                target_app.setWindowIcon(icon)
            return icon
        logger.warning("Application icon at '%s' could not be loaded as a valid QIcon.", icon_path)
    else:
        logger.warning("Application icon file not found at '%s'.", icon_path)
    return None


def center_window(widget: QWidget) -> None:
    """Center a top-level window on the available primary screen."""
    app = QApplication.instance()
    if not app:
        return
    screen = app.primaryScreen()
    if screen:
        geo = screen.availableGeometry()
        x = geo.x() + max(0, (geo.width() - widget.width()) // 2)
        y = geo.y() + max(0, (geo.height() - widget.height()) // 2)
        widget.move(x, y)


class ApplicationController:
    """Manages high-level view transitions based on application state."""

    def __init__(
        self,
        config: AppConfig | None = None,
        init_service: InitializationService | None = None,
        auth_service: AuthenticationService | None = None,
        vault_service: VaultService | None = None,
        session_manager: SessionManager | None = None,
        settings_service: SettingsService | None = None,
        clipboard_service: ClipboardService | None = None,
    ) -> None:
        self.config = config or AppConfig()
        self.init_service = init_service or InitializationService(self.config)
        self.auth_service = auth_service or AuthenticationService()
        self.vault_service = vault_service or VaultService(self.config)
        self.settings_service = settings_service or SettingsService(self.config)
        self.clipboard_service = clipboard_service or ClipboardService.instance()

        # Connect application exit to secure clipboard cleanup
        app = QApplication.instance()
        if app is not None:
            try:
                app.aboutToQuit.connect(self.clipboard_service.clear_if_owned)
            except Exception:
                pass

        # Configure global application icon if QApplication exists
        setup_application_icon()

        # Apply saved theme before any window is rendered
        from app.ui.theme import ThemeManager
        ThemeManager.instance().apply_theme(self.settings_service.get_settings().theme)

        # Initialize or configure SessionManager with saved auto-lock timeout
        saved_timeout = self.settings_service.get_settings().auto_lock_timeout
        if session_manager is not None:
            self.session_manager = session_manager
            self.session_manager.set_countdown_seconds(saved_timeout)
        else:
            self.session_manager = SessionManager(countdown_seconds=saved_timeout)

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
        center_window(wizard)

        result = wizard.exec()
        if result == QDialog.DialogCode.Accepted and wizard.is_setup_successful():
            logger.info("Setup completed successfully. Transitioning to LOCKED view.")
            self.vault_service.lock_vault()
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
        center_window(locked_view)
        locked_view.show()
        return 0

    def _show_unlocked_view(self, vault: DecryptedVault) -> int:
        if vault is None:
            logger.error("Attempted to show UnlockedView with vault=None.")
            raise ValueError("vault cannot be None when displaying UnlockedView.")
        login_id = self.init_service.get_login_id() or "Default User"
        unlocked_view = UnlockedView(
            vault=vault,
            login_id=login_id,
            vault_service=self.vault_service,
            session_manager=self.session_manager,
            settings_service=self.settings_service,
            clipboard_service=self.clipboard_service,
        )
        self.current_window = unlocked_view

        # Wire lock action back to locked state
        unlocked_view.lock_requested.connect(self._on_vault_locked)
        center_window(unlocked_view)
        unlocked_view.show()
        return 0

    def _on_vault_unlocked(self, vault: DecryptedVault) -> None:
        logger.info("Vault unlocked successfully. Transitioning to UNLOCKED view.")
        if self.current_window:
            self.current_window.close()
        self._show_unlocked_view(vault)

    def _on_vault_locked(self) -> None:
        logger.info("Lock requested. Locking vault session and transitioning to LOCKED view.")
        if self.current_window and hasattr(self.current_window, "session_manager"):
            self.current_window.session_manager.stop_session()
        self.clipboard_service.clear_if_owned()
        self.vault_service.lock_vault()
        if self.current_window:
            self.current_window.close()
        self._show_locked_view()

    def _on_dev_reset(self) -> None:
        logger.info("Reset requested. Relaunching First-Run Setup Wizard.")
        self._launch_setup_wizard()


def run_gui(
    config: AppConfig | None = None,
    auth_service: AuthenticationService | None = None,
    vault_service: VaultService | None = None,
    session_manager: SessionManager | None = None,
    clipboard_service: ClipboardService | None = None,
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

    # Set Windows AppUserModelID for taskbar icon grouping
    if sys.platform == "win32":
        try:
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("SecureVault.SecureVault.1.0")
        except Exception:
            pass

    # Configure application-wide window icon
    setup_application_icon(app)

    controller = ApplicationController(
        config=config,
        auth_service=auth_service,
        vault_service=vault_service,
        session_manager=session_manager,
        clipboard_service=clipboard_service,
    )
    controller.start()

    # If a window is currently visible, start event loop
    if controller.current_window and controller.current_window.isVisible():
        return app.exec()
    return 0

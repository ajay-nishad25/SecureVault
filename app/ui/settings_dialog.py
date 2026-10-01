"""SecureVault — Settings Modal Dialog (Milestone M8).

Provides the Settings modal dialog with sidebar navigation:
    - General (Appearance: Dark / Light theme selection)
    - Security (Auto-Lock timeout: 2, 5, 10, 15 minutes & Master Password rotation)
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QButtonGroup,
    QDialog,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QRadioButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from app.core.exceptions import (
    AuthenticationError,
    InvalidPasswordInputError,
    SecurityError,
    StorageError,
)
from app.core.logging import get_logger
from app.core.validation import validate_master_password
from app.services.session_manager import SessionManager
from app.services.settings_service import SettingsService
from app.services.vault_service import VaultService
from app.ui.theme import DARK_THEME, LIGHT_THEME, ThemeManager

logger = get_logger("ui.settings_dialog")


class SettingsDialog(QDialog):
    """Modal Settings dialog with sidebar navigation for preferences and security."""

    theme_changed = Signal(str)
    timeout_changed = Signal(int)
    password_changed = Signal()

    def __init__(
        self,
        settings_service: SettingsService | None = None,
        session_manager: SessionManager | None = None,
        vault_service: VaultService | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._settings_service = settings_service or SettingsService()
        self._session_manager = session_manager
        self._vault_service = vault_service

        self.setWindowTitle("Settings — SecureVault")
        self.setModal(True)
        self.resize(700, 520)
        self.setMinimumSize(640, 440)

        self._init_ui()

    def _init_ui(self) -> None:
        """Initialize the settings dialog layout and component hierarchy."""
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(20, 16, 20, 16)
        main_layout.setSpacing(12)

        # -------------------------------------------------------------
        # Top Header Bar: "Settings" title and close "✕" button
        # -------------------------------------------------------------
        top_bar = QHBoxLayout()
        top_bar.setContentsMargins(0, 0, 0, 0)

        title_label = QLabel("Settings")
        title_label.setObjectName("SettingsTitleLabel")
        top_bar.addWidget(title_label)

        top_bar.addStretch(1)

        self.close_btn = QPushButton("✕")
        self.close_btn.setObjectName("SettingsCloseButton")
        self.close_btn.setFixedSize(30, 30)
        self.close_btn.clicked.connect(self.reject)
        top_bar.addWidget(self.close_btn)

        main_layout.addLayout(top_bar)

        # Divider line
        divider = QFrame()
        divider.setObjectName("SettingsDivider")
        divider.setFrameShape(QFrame.Shape.HLine)
        divider.setFrameShadow(QFrame.Shadow.Sunken)
        main_layout.addWidget(divider)

        # -------------------------------------------------------------
        # Body Layout: Left Sidebar + Right Stacked Content
        # -------------------------------------------------------------
        body_layout = QHBoxLayout()
        body_layout.setSpacing(16)
        body_layout.setContentsMargins(0, 4, 0, 0)

        # Left Navigation Sidebar
        self.sidebar = QListWidget()
        self.sidebar.setObjectName("SettingsSidebar")
        self.sidebar.setFixedWidth(180)
        self.sidebar.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        self.general_item = QListWidgetItem("⚙ General")
        self.general_item.setData(Qt.ItemDataRole.UserRole, "general")
        self.sidebar.addItem(self.general_item)

        self.security_item = QListWidgetItem("🔒 Security")
        self.security_item.setData(Qt.ItemDataRole.UserRole, "security")
        self.sidebar.addItem(self.security_item)

        body_layout.addWidget(self.sidebar)

        # Right Stacked Content Area
        self.content_stack = QStackedWidget()
        self.content_stack.setObjectName("SettingsContentStack")

        # Page 0: General Tab
        self.general_page = self._create_general_page()
        self.content_stack.addWidget(self.general_page)

        # Page 1: Security Tab
        self.security_page = self._create_security_page()
        self.content_stack.addWidget(self.security_page)

        body_layout.addWidget(self.content_stack, stretch=1)
        main_layout.addLayout(body_layout)

        self.setLayout(main_layout)

        # Wire navigation
        self.sidebar.currentRowChanged.connect(self._on_sidebar_changed)
        # Select General by default
        self.sidebar.setCurrentRow(0)

    def _create_general_page(self) -> QWidget:
        """Create the General settings page (Appearance: Dark / Light theme)."""
        page = QWidget()
        page.setObjectName("GeneralPage")
        layout = QVBoxLayout(page)
        layout.setContentsMargins(12, 4, 12, 12)
        layout.setSpacing(14)

        header = QLabel("General")
        header.setObjectName("GeneralHeader")
        layout.addWidget(header)

        # Section Card: Appearance
        appearance_card = QFrame()
        appearance_card.setObjectName("AppearanceSection")
        card_layout = QVBoxLayout(appearance_card)
        card_layout.setSpacing(10)

        section_title = QLabel("Appearance")
        section_title.setObjectName("AppearanceTitle")
        card_layout.addWidget(section_title)

        description = QLabel(
            "Select your preferred application color theme interface."
        )
        description.setObjectName("AppearanceDescription")
        description.setWordWrap(True)
        card_layout.addWidget(description)

        # Theme Radio Buttons
        self.theme_button_group = QButtonGroup(self)

        radio_layout = QHBoxLayout()
        radio_layout.setSpacing(24)

        self.dark_radio = QRadioButton("Dark")
        self.dark_radio.setObjectName("DarkThemeRadio")
        self.theme_button_group.addButton(self.dark_radio, 0)
        radio_layout.addWidget(self.dark_radio)

        self.light_radio = QRadioButton("Light")
        self.light_radio.setObjectName("LightThemeRadio")
        self.theme_button_group.addButton(self.light_radio, 1)
        radio_layout.addWidget(self.light_radio)

        radio_layout.addStretch()
        card_layout.addLayout(radio_layout)

        # Set initial selection from SettingsService
        current_theme = self._settings_service.get_settings().theme
        if current_theme == LIGHT_THEME:
            self.light_radio.setChecked(True)
        else:
            self.dark_radio.setChecked(True)

        self.dark_radio.toggled.connect(self._on_theme_radio_toggled)

        self.theme_status = QLabel(f"Current Theme: <b>{current_theme.capitalize()}</b>")
        self.theme_status.setObjectName("CurrentThemeStatus")
        card_layout.addWidget(self.theme_status)

        layout.addWidget(appearance_card)
        layout.addStretch(1)
        return page

    def _create_security_page(self) -> QWidget:
        """Create the Security settings page (Auto-Lock & Master Password)."""
        page = QWidget()
        page.setObjectName("SecurityPage")
        layout = QVBoxLayout(page)
        layout.setContentsMargins(12, 4, 12, 12)
        layout.setSpacing(14)

        header = QLabel("Security")
        header.setObjectName("SecurityHeader")
        layout.addWidget(header)

        # Section Card 1: Auto-Lock
        autolock_card = QFrame()
        autolock_card.setObjectName("AutoLockSection")
        card1_layout = QVBoxLayout(autolock_card)
        card1_layout.setSpacing(10)

        autolock_title = QLabel("Auto-Lock")
        autolock_title.setObjectName("AutoLockTitle")
        card1_layout.addWidget(autolock_title)

        autolock_desc = QLabel(
            "Select the inactivity timeout duration before the vault automatically locks."
        )
        autolock_desc.setObjectName("AutoLockDescription")
        autolock_desc.setWordWrap(True)
        card1_layout.addWidget(autolock_desc)

        # Auto-Lock Radio Options: 2, 5, 10, 15 minutes
        self.timeout_button_group = QButtonGroup(self)
        timeout_layout = QHBoxLayout()
        timeout_layout.setSpacing(16)

        self.radio_2m = QRadioButton("2 minutes")
        self.radio_2m.setObjectName("AutoLockRadio2m")
        self.timeout_button_group.addButton(self.radio_2m, 120)
        timeout_layout.addWidget(self.radio_2m)

        self.radio_5m = QRadioButton("5 minutes")
        self.radio_5m.setObjectName("AutoLockRadio5m")
        self.timeout_button_group.addButton(self.radio_5m, 300)
        timeout_layout.addWidget(self.radio_5m)

        self.radio_10m = QRadioButton("10 minutes")
        self.radio_10m.setObjectName("AutoLockRadio10m")
        self.timeout_button_group.addButton(self.radio_10m, 600)
        timeout_layout.addWidget(self.radio_10m)

        self.radio_15m = QRadioButton("15 minutes")
        self.radio_15m.setObjectName("AutoLockRadio15m")
        self.timeout_button_group.addButton(self.radio_15m, 900)
        timeout_layout.addWidget(self.radio_15m)

        timeout_layout.addStretch()
        card1_layout.addLayout(timeout_layout)

        # Initial check based on saved setting
        current_timeout = self._settings_service.get_settings().auto_lock_timeout
        if current_timeout == 300:
            self.radio_5m.setChecked(True)
        elif current_timeout == 600:
            self.radio_10m.setChecked(True)
        elif current_timeout == 900:
            self.radio_15m.setChecked(True)
        else:
            self.radio_2m.setChecked(True)

        self.timeout_button_group.idToggled.connect(self._on_timeout_radio_toggled)

        timeout_min = current_timeout // 60
        self.timeout_status = QLabel(
            f"Current Timeout: <b>{timeout_min} minutes</b> (+ 15s grace period)"
        )
        self.timeout_status.setObjectName("CurrentTimeoutStatus")
        card1_layout.addWidget(self.timeout_status)

        layout.addWidget(autolock_card)

        # Section Card 2: Master Password
        password_card = QFrame()
        password_card.setObjectName("MasterPasswordSection")
        card2_layout = QVBoxLayout(password_card)
        card2_layout.setSpacing(10)

        password_title = QLabel("Master Password")
        password_title.setObjectName("MasterPasswordTitle")
        card2_layout.addWidget(password_title)

        password_desc = QLabel(
            "Change the master password protecting your encrypted vault."
        )
        password_desc.setObjectName("MasterPasswordDescription")
        password_desc.setWordWrap(True)
        card2_layout.addWidget(password_desc)

        # Form Inputs (masked)
        form_layout = QFormLayout()
        form_layout.setSpacing(8)

        self.current_pwd_input = QLineEdit()
        self.current_pwd_input.setObjectName("CurrentPasswordInput")
        self.current_pwd_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.current_pwd_input.setPlaceholderText("Enter current master password")
        form_layout.addRow("Current Master Password:", self.current_pwd_input)

        self.new_pwd_input = QLineEdit()
        self.new_pwd_input.setObjectName("NewPasswordInput")
        self.new_pwd_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.new_pwd_input.setPlaceholderText("Enter new master password (min. 8 characters)")
        form_layout.addRow("New Master Password:", self.new_pwd_input)

        self.confirm_pwd_input = QLineEdit()
        self.confirm_pwd_input.setObjectName("ConfirmPasswordInput")
        self.confirm_pwd_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.confirm_pwd_input.setPlaceholderText("Confirm new master password")
        form_layout.addRow("Confirm New Master Password:", self.confirm_pwd_input)

        card2_layout.addLayout(form_layout)

        # Change Button
        btn_row = QHBoxLayout()
        self.change_pwd_btn = QPushButton("Change Master Password")
        self.change_pwd_btn.setObjectName("ChangePasswordButton")
        self.change_pwd_btn.clicked.connect(self._on_change_password_clicked)
        btn_row.addWidget(self.change_pwd_btn)
        btn_row.addStretch()
        card2_layout.addLayout(btn_row)

        # Required Note (Section 14)
        self.pwd_note_label = QLabel(
            "NOTE: After successfully changing your master password, SecureVault will "
            "lock the vault and return you to the login screen. You must use your "
            "new master password to unlock the vault again."
        )
        self.pwd_note_label.setObjectName("PasswordNoteLabel")
        self.pwd_note_label.setWordWrap(True)
        card2_layout.addWidget(self.pwd_note_label)

        # Status / Feedback label
        self.pwd_status_label = QLabel("")
        self.pwd_status_label.setObjectName("PasswordStatusLabel")
        self.pwd_status_label.setWordWrap(True)
        card2_layout.addWidget(self.pwd_status_label)

        layout.addWidget(password_card)
        layout.addStretch(1)
        return page

    def _on_theme_radio_toggled(self, checked: bool) -> None:
        """Handle theme radio button toggle (Dark <-> Light)."""
        if not checked and self.dark_radio.isChecked():
            return

        selected_theme = DARK_THEME if self.dark_radio.isChecked() else LIGHT_THEME
        logger.info("Theme selection changed to: %s", selected_theme)

        # Apply immediately at runtime
        ThemeManager.instance().apply_theme(selected_theme)
        # Persist through SettingsService
        self._settings_service.set_theme(selected_theme)
        # Update status text
        self.theme_status.setText(f"Current Theme: <b>{selected_theme.capitalize()}</b>")
        self.theme_changed.emit(selected_theme)

    def _on_timeout_radio_toggled(self, timeout_id: int, checked: bool) -> None:
        """Handle auto-lock timeout radio toggle (120, 300, 600, 900 seconds)."""
        if not checked:
            return

        logger.info("Auto-lock timeout changed to: %d seconds", timeout_id)

        # Persist through SettingsService
        self._settings_service.set_auto_lock_timeout(timeout_id)

        # Live update session manager if active
        if self._session_manager is not None:
            self._session_manager.set_countdown_seconds(timeout_id)

        # Update status text
        timeout_min = timeout_id // 60
        self.timeout_status.setText(
            f"Current Timeout: <b>{timeout_min} minutes</b> (+ 15s grace period)"
        )
        self.timeout_changed.emit(timeout_id)

    def _on_change_password_clicked(self) -> None:
        """Execute master password change workflow with validation and DEK re-wrapping."""
        cur_pwd = self.current_pwd_input.text()
        new_pwd = self.new_pwd_input.text()
        confirm_pwd = self.confirm_pwd_input.text()

        if not cur_pwd:
            self.pwd_status_label.setText("Current master password cannot be empty.")
            self.pwd_status_label.setStyleSheet("color: #ee5555; font-size: 11px;")
            return

        if not new_pwd:
            self.pwd_status_label.setText("Master password cannot be empty.")
            self.pwd_status_label.setStyleSheet("color: #ee5555; font-size: 11px;")
            return

        is_valid, err_msg = validate_master_password(new_pwd, confirm_pwd)
        if not is_valid:
            self.pwd_status_label.setText(err_msg)
            self.pwd_status_label.setStyleSheet("color: #ee5555; font-size: 11px;")
            return

        if cur_pwd == new_pwd:
            self.pwd_status_label.setText(
                "New master password cannot be the same as the current password."
            )
            self.pwd_status_label.setStyleSheet("color: #ee5555; font-size: 11px;")
            return

        if not self._vault_service:
            self.pwd_status_label.setText("VaultService unavailable.")
            self.pwd_status_label.setStyleSheet("color: #ee5555; font-size: 11px;")
            return

        try:
            self._vault_service.change_master_password(
                current_password=cur_pwd,
                new_password=new_pwd,
                confirm_password=confirm_pwd,
            )
        except AuthenticationError as err:
            self.pwd_status_label.setText("Incorrect current master password.")
            self.pwd_status_label.setStyleSheet("color: #ee5555; font-size: 11px;")
            return
        except (InvalidPasswordInputError, SecurityError, StorageError) as err:
            self.pwd_status_label.setText(str(err))
            self.pwd_status_label.setStyleSheet("color: #ee5555; font-size: 11px;")
            return
        except Exception as err:
            logger.error("Unexpected error during master password change: %s", err)
            self.pwd_status_label.setText(f"Failed to change master password: {err}")
            self.pwd_status_label.setStyleSheet("color: #ee5555; font-size: 11px;")
            return
        finally:
            # Wipe in-memory input widgets
            self.current_pwd_input.clear()
            self.new_pwd_input.clear()
            self.confirm_pwd_input.clear()
            cur_pwd = ""
            new_pwd = ""
            confirm_pwd = ""

        # Show success message
        QMessageBox.information(
            self,
            "Password Changed — SecureVault",
            "Master password successfully changed.\n\n"
            "The vault will now lock. Please authenticate with your new master password.",
        )
        self.password_changed.emit()
        self.accept()

    def _on_sidebar_changed(self, row: int) -> None:
        """Switch active stacked widget page on sidebar selection."""
        self.content_stack.setCurrentIndex(row)

    def center_on_parent(self) -> None:
        """Center dialog relative to the parent window or screen."""
        parent_widget = self.parentWidget()
        if parent_widget:
            p_geo = parent_widget.geometry()
            x = p_geo.x() + max(0, (p_geo.width() - self.width()) // 2)
            y = p_geo.y() + max(0, (p_geo.height() - self.height()) // 2)
            self.move(x, y)

    def showEvent(self, event) -> None:
        """Center dialog on show."""
        super().showEvent(event)
        self.center_on_parent()

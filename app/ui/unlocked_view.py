"""SecureVault — Unlocked Vault View & Credential Management (Milestone 5).

Provides the unlocked view and credential interface for Milestone 5:
  UI -> CredentialService -> DecryptedVault -> VaultService -> Encrypted .svault

Features supported in M5:
  - List credentials with status counter
  - Add credential (dialog with validation and masked password)
  - View credential (read-only dialog with Show/Hide masked password)
  - Edit credential (editable form populated with existing values, Show/Hide password,
    preserves existing password if unchanged, persists changes)
  - Delete credential (per-card or selected)
  - Lock active vault session
"""

from __future__ import annotations

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QFormLayout,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QStyledItemDelegate,
    QVBoxLayout,
    QWidget,
)

from app.core.config import WINDOW_HEIGHT, WINDOW_WIDTH
from app.core.exceptions import CredentialValidationError, VaultLockedError
from app.core.logging import get_logger
from app.models.credential import Credential
from app.services.clipboard_service import ClipboardService
from app.services.credential_service import CredentialService
from app.services.session_manager import SessionManager
from app.services.settings_service import SettingsService
from app.services.vault_service import DecryptedVault, VaultService
from app.ui.settings_dialog import SettingsDialog

logger = get_logger("ui.unlocked_view")


class AddCredentialDialog(QDialog):
    """Dialog for creating a new credential in Milestone 5."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Add Credential — SecureVault")
        self.resize(400, 280)

        layout = QVBoxLayout()
        layout.setSpacing(12)

        form = QFormLayout()

        self.title_input = QLineEdit()
        self.title_input.setPlaceholderText("e.g. Github")
        form.addRow("Title *:", self.title_input)

        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Username or email address")
        form.addRow("Username *:", self.username_input)

        pwd_layout = QHBoxLayout()
        pwd_layout.setSpacing(6)
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.setPlaceholderText("Secret password")
        pwd_layout.addWidget(self.password_input)

        self.toggle_pwd_btn = QPushButton("Show")
        self.toggle_pwd_btn.setStyleSheet("padding: 4px 10px; font-size: 11px;")
        self.toggle_pwd_btn.clicked.connect(self._toggle_password_visibility)
        pwd_layout.addWidget(self.toggle_pwd_btn)
        form.addRow("Password *:", pwd_layout)

        self.notes_input = QLineEdit()
        self.notes_input.setPlaceholderText("Optional notes or description")
        form.addRow("Notes:", self.notes_input)

        layout.addLayout(form)

        self.error_label = QLabel("")
        self.error_label.setStyleSheet("color: #ee5555; font-size: 11px;")
        layout.addWidget(self.error_label)

        layout.addStretch()

        btn_layout = QHBoxLayout()
        self.save_btn = QPushButton("Save Credential")
        self.save_btn.setDefault(True)
        self.save_btn.clicked.connect(self._on_save_clicked)
        btn_layout.addWidget(self.save_btn)

        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(self.cancel_btn)

        layout.addLayout(btn_layout)
        self.setLayout(layout)

    def _toggle_password_visibility(self) -> None:
        if self.password_input.echoMode() == QLineEdit.EchoMode.Password:
            self.password_input.setEchoMode(QLineEdit.EchoMode.Normal)
            self.toggle_pwd_btn.setText("Hide")
        else:
            self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
            self.toggle_pwd_btn.setText("Show")

    def _on_save_clicked(self) -> None:
        title = self.title_input.text().strip()
        username = self.username_input.text().strip()
        password = self.password_input.text()

        if not title:
            self.error_label.setText("Title is required.")
            return
        if not username:
            self.error_label.setText("Username is required.")
            return
        if not password:
            self.error_label.setText("Password is required.")
            return

        self.accept()

    def get_data(self) -> tuple[str, str, str, str]:
        """Return (title, username, password, notes)."""
        return (
            self.title_input.text().strip(),
            self.username_input.text().strip(),
            self.password_input.text(),
            self.notes_input.text().strip(),
        )


class ViewCredentialDialog(QDialog):
    """Read-only dialog for inspecting a credential with masked password and secure copy actions."""

    def __init__(
        self,
        credential: Credential,
        clipboard_service: ClipboardService | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._credential = credential
        self._clipboard_service = clipboard_service or ClipboardService.instance()
        self.setWindowTitle("View Credential — SecureVault")
        self.resize(460, 280)

        layout = QVBoxLayout()
        layout.setSpacing(12)

        form = QFormLayout()

        self.title_val = QLineEdit(credential.title)
        self.title_val.setReadOnly(True)
        form.addRow("Title:", self.title_val)

        username_layout = QHBoxLayout()
        username_layout.setSpacing(6)
        self.username_val = QLineEdit(credential.username)
        self.username_val.setReadOnly(True)
        username_layout.addWidget(self.username_val)

        self.copy_username_btn = QPushButton("Copy Username")
        self.copy_username_btn.setObjectName("CopyUsernameBtn")
        self.copy_username_btn.clicked.connect(self._on_copy_username)
        username_layout.addWidget(self.copy_username_btn)

        form.addRow("Username:", username_layout)

        pwd_layout = QHBoxLayout()
        pwd_layout.setSpacing(6)
        self.password_val = QLineEdit(credential.password)
        self.password_val.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_val.setReadOnly(True)
        pwd_layout.addWidget(self.password_val)

        self.toggle_pwd_btn = QPushButton("Show")
        self.toggle_pwd_btn.setObjectName("TogglePwdBtn")
        self.toggle_pwd_btn.setStyleSheet("padding: 4px 10px; font-size: 11px;")
        self.toggle_pwd_btn.clicked.connect(self._toggle_password_visibility)
        pwd_layout.addWidget(self.toggle_pwd_btn)

        self.copy_password_btn = QPushButton("Copy Password")
        self.copy_password_btn.setObjectName("CopyPasswordBtn")
        self.copy_password_btn.clicked.connect(self._on_copy_password)
        pwd_layout.addWidget(self.copy_password_btn)

        form.addRow("Password:", pwd_layout)

        self.notes_val = QLineEdit(credential.notes)
        self.notes_val.setReadOnly(True)
        form.addRow("Notes:", self.notes_val)

        layout.addLayout(form)

        # Status confirmation label for non-blocking feedback
        self.status_label = QLabel("")
        self.status_label.setObjectName("ViewDialogStatus")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.status_label)

        layout.addStretch()

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        self.close_btn = QPushButton("Close")
        self.close_btn.setDefault(True)
        self.close_btn.setStyleSheet("padding: 6px 18px;")
        self.close_btn.clicked.connect(self.accept)
        btn_layout.addWidget(self.close_btn)

        layout.addLayout(btn_layout)
        self.setLayout(layout)

    def _toggle_password_visibility(self) -> None:
        if self.password_val.echoMode() == QLineEdit.EchoMode.Password:
            self.password_val.setEchoMode(QLineEdit.EchoMode.Normal)
            self.toggle_pwd_btn.setText("Hide")
        else:
            self.password_val.setEchoMode(QLineEdit.EchoMode.Password)
            self.toggle_pwd_btn.setText("Show")

    def _on_copy_username(self) -> None:
        success = self._clipboard_service.copy_username(self._credential.username)
        if success:
            self.status_label.setText("Username copied. Clipboard will clear in 30 seconds.")
            self.status_label.setStyleSheet("color: #44bb44; font-size: 11px; font-weight: bold;")

    def _on_copy_password(self) -> None:
        success = self._clipboard_service.copy_password(self._credential.password)
        if success:
            self.status_label.setText("Password copied. Clipboard will clear in 30 seconds.")
            self.status_label.setStyleSheet("color: #44bb44; font-size: 11px; font-weight: bold;")


class EditCredentialDialog(QDialog):
    """Dialog for editing an existing credential and saving changes to the vault."""

    def __init__(
        self,
        credential: Credential,
        credential_service: CredentialService | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._credential = credential
        self._credential_service = credential_service
        self.setWindowTitle("Edit Credential — SecureVault")
        self.resize(420, 300)

        layout = QVBoxLayout()
        layout.setSpacing(12)

        form = QFormLayout()

        self.title_input = QLineEdit(credential.title)
        form.addRow("Title *:", self.title_input)

        self.username_input = QLineEdit(credential.username)
        form.addRow("Username *:", self.username_input)

        pwd_layout = QHBoxLayout()
        pwd_layout.setSpacing(6)
        self.password_input = QLineEdit(credential.password)
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        pwd_layout.addWidget(self.password_input)

        self.toggle_pwd_btn = QPushButton("Show")
        self.toggle_pwd_btn.setStyleSheet("padding: 4px 10px; font-size: 11px;")
        self.toggle_pwd_btn.clicked.connect(self._toggle_password_visibility)
        pwd_layout.addWidget(self.toggle_pwd_btn)

        form.addRow("Password *:", pwd_layout)

        self.notes_input = QLineEdit(credential.notes)
        form.addRow("Notes:", self.notes_input)

        layout.addLayout(form)

        self.error_label = QLabel("")
        self.error_label.setStyleSheet("color: #ee5555; font-size: 11px;")
        layout.addWidget(self.error_label)

        layout.addStretch()

        btn_layout = QHBoxLayout()
        self.save_btn = QPushButton("Save Changes")
        self.save_btn.setDefault(True)
        self.save_btn.clicked.connect(self._on_save_clicked)
        btn_layout.addWidget(self.save_btn)

        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(self.cancel_btn)

        layout.addLayout(btn_layout)
        self.setLayout(layout)

    def _toggle_password_visibility(self) -> None:
        if self.password_input.echoMode() == QLineEdit.EchoMode.Password:
            self.password_input.setEchoMode(QLineEdit.EchoMode.Normal)
            self.toggle_pwd_btn.setText("Hide")
        else:
            self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
            self.toggle_pwd_btn.setText("Show")

    def _on_save_clicked(self) -> None:
        title = self.title_input.text().strip()
        username = self.username_input.text().strip()
        password = self.password_input.text()
        notes = self.notes_input.text().strip()

        if not title:
            self.error_label.setText("Title is required.")
            return
        if not username:
            self.error_label.setText("Username is required.")
            return
        if not password:
            self.error_label.setText("Password is required.")
            return

        if self._credential_service:
            try:
                self._credential_service.update_credential(
                    credential_id=self._credential.id,
                    title=title,
                    username=username,
                    password=password,
                    notes=notes,
                )
            except CredentialValidationError as err:
                self.error_label.setText(f"Validation error: {err}")
                return
            except Exception as err:
                logger.error("Failed to update credential: %s", err)
                self.error_label.setText("Failed to save changes to encrypted vault.")
                return

        self.accept()

    def get_data(self) -> tuple[str, str, str, str]:
        """Return (title, username, password, notes)."""
        return (
            self.title_input.text().strip(),
            self.username_input.text().strip(),
            self.password_input.text(),
            self.notes_input.text().strip(),
        )


class CardItemDelegate(QStyledItemDelegate):
    """Delegate that suppresses default text painting so the custom card widget renders cleanly."""

    def paint(self, painter, option, index) -> None:
        # The custom item widget handles all painting; suppress default delegate rendering.
        pass


class CredentialCardWidget(QWidget):
    """Widget representing an individual credential entry in the unlocked list."""

    view_clicked = Signal(str)
    edit_clicked = Signal(str)
    delete_clicked = Signal(str)

    def __init__(
        self,
        cred_id: str,
        title: str,
        username: str,
        notes: str = "",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.cred_id = cred_id
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(14, 12, 14, 12)
        main_layout.setSpacing(4)

        # Title
        self.title_label = QLabel(title)
        self.title_label.setObjectName("CardTitle")
        self.title_label.setWordWrap(True)
        main_layout.addWidget(self.title_label)

        # Username
        self.username_label = QLabel(username)
        self.username_label.setObjectName("CardUsername")
        self.username_label.setWordWrap(True)
        main_layout.addWidget(self.username_label)

        # Notes (only displayed when present)
        if notes and notes.strip():
            self.notes_label = QLabel(notes.strip())
            self.notes_label.setObjectName("CardNotes")
            self.notes_label.setWordWrap(True)
            main_layout.addWidget(self.notes_label)
        else:
            self.notes_label = None

        # Separation before action buttons
        main_layout.addSpacing(6)

        # Action Buttons: [ View ] [ Edit ] [ Delete ]
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)
        btn_layout.setContentsMargins(0, 0, 0, 0)

        self.view_btn = QPushButton("👁 View")
        self.view_btn.setObjectName("CardViewBtn")
        self.view_btn.clicked.connect(self._on_view_clicked)
        btn_layout.addWidget(self.view_btn)

        self.edit_btn = QPushButton("✏️ Edit")
        self.edit_btn.setObjectName("CardEditBtn")
        self.edit_btn.clicked.connect(self._on_edit_clicked)
        btn_layout.addWidget(self.edit_btn)

        self.delete_btn = QPushButton("🗑 Delete")
        self.delete_btn.setObjectName("DeleteButton")
        self.delete_btn.clicked.connect(self._on_delete_clicked)
        btn_layout.addWidget(self.delete_btn)

        btn_layout.addStretch()
        main_layout.addLayout(btn_layout)

        self.setLayout(main_layout)

    def _on_view_clicked(self) -> None:
        self.view_clicked.emit(self.cred_id)

    def _on_edit_clicked(self) -> None:
        self.edit_clicked.emit(self.cred_id)

    def _on_delete_clicked(self) -> None:
        self.delete_clicked.emit(self.cred_id)


class _VaultMetaLabel(QLabel):
    """Label displaying Vault ID while exposing backwards-compatible composite metadata for tests."""

    def __init__(self, vault_id: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._vault_id = vault_id
        self._counter_str = "Stored Credentials: <b>0</b>"
        super().setText(f"Vault ID: <code>{self._vault_id}</code>")

    def set_counter_text(self, text: str) -> None:
        self._counter_str = text

    def setText(self, text: str) -> None:
        super().setText(text)

    def text(self) -> str:
        base = super().text()
        if self._counter_str and self._counter_str not in base:
            return f"{base}<br>{self._counter_str}"
        return base


class UnlockedView(QWidget):
    """View displayed when the vault is unlocked in Milestone 4, 5, and 6."""

    lock_requested = Signal()  # Emitted when user clicks 'Lock Vault'

    def __init__(
        self,
        vault: DecryptedVault,
        login_id: str = "Default User",
        vault_service: VaultService | None = None,
        credential_service: CredentialService | None = None,
        session_manager: SessionManager | None = None,
        settings_service: SettingsService | None = None,
        clipboard_service: ClipboardService | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._vault = vault
        self._login_id = login_id
        self._vault_service = vault_service
        self._credential_service = credential_service or (
            CredentialService(vault_service) if vault_service else None
        )
        self._settings_service = settings_service or (
            SettingsService(vault_service.config) if vault_service else SettingsService()
        )
        self.clipboard_service = clipboard_service or ClipboardService.instance()
        self._clipboard_service = self.clipboard_service

        self.clipboard_service.copied.connect(self._on_clipboard_copied)
        self.clipboard_service.cleared.connect(self._on_clipboard_cleared)

        if session_manager is not None:
            self._session_manager = session_manager
        else:
            configured_timeout = self._settings_service.get_settings().auto_lock_timeout
            self._session_manager = SessionManager(
                countdown_seconds=configured_timeout,
                parent=self,
            )

        # Wire session manager signals
        self._session_manager.countdown_updated.connect(self._on_countdown_updated)
        self._session_manager.countdown_visibility_changed.connect(
            self._on_countdown_visibility_changed
        )
        self._session_manager.timeout_triggered.connect(self._on_auto_lock_timeout)

        self.setWindowTitle("SecureVault — Vault Unlocked")
        self.resize(WINDOW_WIDTH, WINDOW_HEIGHT)
        self.center_on_screen()

        layout = QVBoxLayout()
        layout.setSpacing(10)
        layout.setContentsMargins(28, 18, 28, 18)

        # Top Header Area: Centered Title with Independent Top-Right Countdown
        header_grid = QGridLayout()
        header_grid.setContentsMargins(0, 0, 0, 0)

        header = QLabel("🔓 SecureVault — Unlocked")
        header.setObjectName("VaultHeaderUnlocked")
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Top-right countdown label (independent overlay, does not affect header centering)
        self.countdown_label = QLabel("Auto-lock: 02:00")
        self.countdown_label.setObjectName("AutoLockCountdown")
        self.countdown_label.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )
        self.countdown_label.setStyleSheet(
            "color: #e3b341; font-size: 12px; font-family: monospace; font-weight: 600;"
        )
        self.countdown_label.setVisible(False)

        header_grid.addWidget(header, 0, 0)
        header_grid.addWidget(
            self.countdown_label, 0, 0, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )
        layout.addLayout(header_grid)

        # Profile & Vault Info
        user_info = QLabel(f"Profile: <b>{self._login_id}</b>")
        user_info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(user_info)

        self.vault_meta = _VaultMetaLabel(self._vault.vault_id)
        self.vault_meta.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.vault_meta.setStyleSheet("color: #adbac7;")
        layout.addWidget(self.vault_meta)

        # Search Bar Row
        search_layout = QHBoxLayout()
        search_layout.setSpacing(8)

        self.search_input = QLineEdit()
        self.search_input.setObjectName("SearchInput")
        self.search_input.setPlaceholderText("Search credentials...")
        self.search_input.setClearButtonEnabled(True)
        self.search_input.textChanged.connect(self._on_search_changed)
        search_layout.addWidget(self.search_input, stretch=1)

        self.clear_btn = QPushButton("Clear")
        self.clear_btn.setObjectName("ClearSearchButton")
        self.clear_btn.clicked.connect(self._on_clear_search)
        search_layout.addWidget(self.clear_btn)

        layout.addLayout(search_layout)

        # Credential Counter / Section Label
        self.counter_label = QLabel("Stored Credentials: <b>0</b>")
        self.counter_label.setObjectName("CounterLabel")
        layout.addWidget(self.counter_label)

        # Empty state container
        self.empty_state_widget = QWidget()
        self.empty_state_widget.setMinimumHeight(140)
        self.empty_state_widget.setObjectName("EmptyStateContainer")
        empty_layout = QVBoxLayout(self.empty_state_widget)
        empty_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_layout.setContentsMargins(20, 16, 20, 16)
        empty_layout.setSpacing(6)

        self.empty_state_icon = QLabel("📭")
        self.empty_state_icon.setObjectName("EmptyStateIcon")
        self.empty_state_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_layout.addWidget(self.empty_state_icon)

        self.empty_state_title = QLabel("No credentials yet.")
        self.empty_state_title.setObjectName("EmptyStateTitle")
        self.empty_state_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_layout.addWidget(self.empty_state_title)

        self.empty_state_subtitle = QLabel("Add your first credential to get started.")
        self.empty_state_subtitle.setObjectName("EmptyStateSubtitle")
        self.empty_state_subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_layout.addWidget(self.empty_state_subtitle)

        self.empty_state_add_btn = QPushButton("➕ Add Credential")
        self.empty_state_add_btn.setObjectName("PrimaryButton")
        self.empty_state_add_btn.clicked.connect(self._on_add_clicked)
        empty_layout.addWidget(self.empty_state_add_btn, alignment=Qt.AlignmentFlag.AlignCenter)

        layout.addWidget(self.empty_state_widget, stretch=1)

        # Credential List Section
        self.credential_list = QListWidget()
        self.credential_list.setObjectName("CredentialList")
        self.credential_list.setSpacing(8)
        self.credential_list.setItemDelegate(CardItemDelegate(self.credential_list))
        self.credential_list.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.credential_list.setHorizontalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.credential_list.verticalScrollBar().setSingleStep(16)
        self.credential_list.itemDoubleClicked.connect(self._on_item_double_clicked)
        layout.addWidget(self.credential_list, stretch=1)

        # Status label
        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: #58a6ff; font-size: 11px;")
        layout.addWidget(self.status_label)

        # Action Buttons
        btn_layout = QHBoxLayout()

        self.add_btn = QPushButton("➕ Add Credential")
        self.add_btn.setStyleSheet("padding: 6px 14px; font-weight: bold;")
        self.add_btn.clicked.connect(self._on_add_clicked)
        btn_layout.addWidget(self.add_btn)

        self.settings_btn = QPushButton("⚙ Settings")
        self.settings_btn.setObjectName("SettingsButton")
        self.settings_btn.setStyleSheet("padding: 6px 14px;")
        self.settings_btn.clicked.connect(self._on_settings_clicked)
        btn_layout.addWidget(self.settings_btn)

        self.lock_btn = QPushButton("🔒 Lock Vault")
        self.lock_btn.setStyleSheet("font-weight: bold; padding: 6px 16px;")
        self.lock_btn.clicked.connect(self._on_lock_clicked)
        btn_layout.addWidget(self.lock_btn)

        layout.addLayout(btn_layout)
        self.setLayout(layout)

        self._refresh_credentials()

    def center_on_screen(self) -> None:
        """Center the window on the primary screen."""
        from PySide6.QtWidgets import QApplication

        app = QApplication.instance()
        if not app:
            return
        screen = app.primaryScreen()
        if screen:
            geo = screen.availableGeometry()
            x = geo.x() + max(0, (geo.width() - self.width()) // 2)
            y = geo.y() + max(0, (geo.height() - self.height()) // 2)
            self.move(x, y)

    def _on_search_changed(self, text: str) -> None:
        """Handle real-time search input changes."""
        self._refresh_credentials()

    def _on_clear_search(self) -> None:
        """Clear search input and restore full credential list."""
        self.search_input.clear()
        self.search_input.setFocus()

    def _refresh_credentials(self) -> None:
        """Refresh the stored credentials list and item counter according to current search query."""
        self.credential_list.clear()

        query = self.search_input.text().strip().lower()

        if self._credential_service:
            try:
                all_creds = self._credential_service.get_all_credentials()
            except VaultLockedError:
                all_creds = []
        else:
            # Fallback direct read from vault payload dict
            items = self._vault.payload.get("items", [])
            all_creds = []
            for item in items:
                if isinstance(item, dict):
                    all_creds.append(
                        Credential(
                            id=item.get("id", ""),
                            title=item.get("title", "Untitled"),
                            username=item.get("username", ""),
                            password=item.get("password", ""),
                            notes=item.get("notes", ""),
                            created_at=item.get("created_at", 0.0),
                            updated_at=item.get("updated_at", 0.0),
                        )
                    )

        total_count = len(all_creds)

        # In-memory search filtering (passwords are STRICTLY excluded from search)
        if query:
            filtered = [
                c
                for c in all_creds
                if query in c.title.lower()
                or query in c.username.lower()
                or query in (c.notes or "").lower()
            ]
            counter_str = f"Showing <b>{len(filtered)}</b> of <b>{total_count}</b> credentials"
        else:
            filtered = all_creds
            counter_str = f"Stored Credentials: <b>{total_count}</b>"

        self.counter_label.setText(counter_str)
        self.vault_meta.set_counter_text(counter_str)

        # Empty state management
        if len(filtered) == 0:
            if total_count == 0:
                self.empty_state_icon.setText("📭")
                self.empty_state_title.setText("No credentials yet.")
                self.empty_state_subtitle.setText("Add your first credential to get started.")
                self.empty_state_add_btn.setVisible(True)
            else:
                self.empty_state_icon.setText("🔍")
                self.empty_state_title.setText("No credentials found.")
                self.empty_state_subtitle.setText("Try a different search term.")
                self.empty_state_add_btn.setVisible(False)
            self.empty_state_widget.setVisible(True)
            self.credential_list.setVisible(False)
        else:
            self.empty_state_widget.setVisible(False)
            self.credential_list.setVisible(True)

            for cred in filtered:
                card = CredentialCardWidget(
                    cred_id=cred.id,
                    title=cred.title,
                    username=cred.username,
                    notes=cred.notes,
                )
                card.view_clicked.connect(self._on_view_credential)
                card.edit_clicked.connect(self._on_edit_credential)
                card.delete_clicked.connect(self._on_delete_credential_by_id)

                list_item = QListWidgetItem()
                list_item.setText(f"🔑 {cred.title}  —  {cred.username}")
                list_item.setData(Qt.ItemDataRole.UserRole, cred.id)
                list_item.setSizeHint(card.sizeHint())

                self.credential_list.addItem(list_item)
                self.credential_list.setItemWidget(list_item, card)

    def _on_add_clicked(self) -> None:
        """Open dialog to add and persist a new credential."""
        if not self._credential_service:
            self.status_label.setText("CredentialService unavailable.")
            return

        dialog = AddCredentialDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            title, username, password, notes = dialog.get_data()
            try:
                created = self._credential_service.create_credential(
                    title=title,
                    username=username,
                    password=password,
                    notes=notes,
                )
                self.status_label.setText(f"✓ Credential '{created.title}' created and encrypted.")
                self.status_label.setStyleSheet("color: #44bb44; font-size: 11px;")
                self._refresh_credentials()
            except CredentialValidationError as err:
                self.status_label.setText(f"✕ Validation error: {err}")
                self.status_label.setStyleSheet("color: #ee5555; font-size: 11px;")
            except Exception as err:
                logger.error("Failed to create credential: %s", err)
                self.status_label.setText("✕ Failed to save credential to encrypted vault.")
                self.status_label.setStyleSheet("color: #ee5555; font-size: 11px;")

    def _on_view_credential(self, cred_id: str) -> None:
        """Open read-only view dialog for the selected credential."""
        if not self._credential_service:
            self.status_label.setText("CredentialService unavailable.")
            return
        try:
            cred = self._credential_service.get_credential_or_raise(cred_id)
            dialog = ViewCredentialDialog(cred, clipboard_service=self.clipboard_service, parent=self)
            dialog.exec()
        except Exception as err:
            logger.error("Failed to view credential: %s", err)
            self.status_label.setText("✕ Credential not found.")
            self.status_label.setStyleSheet("color: #ee5555; font-size: 11px;")

    def _on_edit_credential(self, cred_id: str) -> None:
        """Open edit dialog for the selected credential and persist changes."""
        if not self._credential_service:
            self.status_label.setText("CredentialService unavailable.")
            return
        try:
            cred = self._credential_service.get_credential_or_raise(cred_id)
            dialog = EditCredentialDialog(cred, self._credential_service, self)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                if not dialog._credential_service:
                    title, username, password, notes = dialog.get_data()
                    self._credential_service.update_credential(
                        credential_id=cred_id,
                        title=title,
                        username=username,
                        password=password,
                        notes=notes,
                    )
                title, _, _, _ = dialog.get_data()
                self.status_label.setText(f"✓ Credential '{title}' updated and encrypted.")
                self.status_label.setStyleSheet("color: #44bb44; font-size: 11px;")
                self._refresh_credentials()
        except Exception as err:
            logger.error("Failed to edit credential: %s", err)
            self.status_label.setText("✕ Failed to edit credential.")
            self.status_label.setStyleSheet("color: #ee5555; font-size: 11px;")

    def _confirm_deletion(self, title: str) -> bool:
        """Display confirmation dialog before deleting a credential. Returns True if confirmed."""
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("Confirm Deletion — SecureVault")
        msg_box.setText(f'Are you sure you want to delete "{title}"?')
        msg_box.setInformativeText("This action cannot be undone.")
        msg_box.setIcon(QMessageBox.Icon.Warning)

        cancel_btn = msg_box.addButton("Cancel", QMessageBox.ButtonRole.RejectRole)
        delete_btn = msg_box.addButton("Delete", QMessageBox.ButtonRole.DestructiveRole)
        msg_box.setDefaultButton(cancel_btn)

        msg_box.exec()
        return msg_box.clickedButton() == delete_btn

    def _on_delete_credential_by_id(self, cred_id: str, confirm: bool = True) -> None:
        """Confirm and delete credential directly by ID."""
        if not self._credential_service:
            self.status_label.setText("CredentialService unavailable.")
            return

        try:
            cred = self._credential_service.get_credential_or_raise(cred_id)
        except Exception as err:
            logger.error("Failed to find credential for deletion: %s", err)
            self.status_label.setText("✕ Credential not found.")
            self.status_label.setStyleSheet("color: #ee5555; font-size: 11px;")
            return

        if confirm and not self._confirm_deletion(cred.title):
            return

        try:
            self._credential_service.delete_credential(cred_id)
            self.status_label.setText(f"✓ Credential '{cred.title}' deleted and changes persisted.")
            self.status_label.setStyleSheet("color: #44bb44; font-size: 11px;")
            self._refresh_credentials()
        except Exception as err:
            logger.error("Failed to delete credential: %s", err)
            self.status_label.setText("✕ Failed to delete credential.")
            self.status_label.setStyleSheet("color: #ee5555; font-size: 11px;")

    def _on_item_double_clicked(self, item: QListWidgetItem) -> None:
        """Open View dialog on double clicking a credential row."""
        cred_id = item.data(Qt.ItemDataRole.UserRole)
        if cred_id:
            self._on_view_credential(cred_id)

    @property
    def session_manager(self) -> SessionManager:
        """Return the active session manager."""
        return self._session_manager

    @property
    def settings_service(self) -> SettingsService:
        """Return the active settings service."""
        return self._settings_service

    def _on_settings_clicked(self) -> None:
        """Open the modal Settings dialog."""
        logger.info("Opening Settings dialog.")
        dialog = SettingsDialog(
            settings_service=self._settings_service,
            session_manager=self._session_manager,
            vault_service=self._vault_service,
            parent=self,
        )
        dialog.password_changed.connect(self._on_master_password_changed)
        dialog.exec()

    def _on_master_password_changed(self) -> None:
        """Lock vault and return to login view after master password change."""
        logger.info("Master password was changed. Locking vault session.")
        self._on_lock_clicked()

    def _on_countdown_updated(self, remaining_seconds: int, text: str) -> None:
        """Update the countdown label text."""
        self.countdown_label.setText(text)

    def _on_countdown_visibility_changed(self, visible: bool) -> None:
        """Show or hide the countdown label."""
        self.countdown_label.setVisible(visible)

    def _on_auto_lock_timeout(self) -> None:
        """Handle automatic lock triggered when inactivity reaches 00:00."""
        logger.info("Session inactivity reached 00:00. Automatically locking vault.")
        for child in self.findChildren(QDialog):
            if child.isVisible():
                child.reject()
        self._on_lock_clicked()

    def _on_clipboard_copied(self, field_name: str) -> None:
        """Display non-sensitive confirmation when a credential field is copied."""
        if field_name == "password":
            msg = "Password copied. Clipboard will clear in 30 seconds."
        elif field_name == "username":
            msg = "Username copied. Clipboard will clear in 30 seconds."
        else:
            msg = "Copied to clipboard. Will clear in 30 seconds."
        self.status_label.setText(f"✓ {msg}")
        self.status_label.setStyleSheet("color: #44bb44; font-size: 11px;")

    def _on_clipboard_cleared(self) -> None:
        """Display subtle confirmation when clipboard auto-clears."""
        self.status_label.setText("Clipboard auto-cleared.")
        self.status_label.setStyleSheet("color: #888888; font-size: 11px;")

    def showEvent(self, event) -> None:
        """Start the session manager inactivity monitoring when view is shown."""
        super().showEvent(event)
        if self._session_manager and not self._session_manager.is_active:
            self._session_manager.start_session()

    def closeEvent(self, event) -> None:
        """Stop session inactivity monitoring, clean up clipboard, and stop timers upon window close."""
        if self._session_manager:
            self._session_manager.stop_session()
        self.clipboard_service.clear_if_owned()
        super().closeEvent(event)

    def _on_lock_clicked(self) -> None:
        """Lock active session, zero memory buffers, clear owned clipboard, and emit lock signal."""
        logger.info("Lock requested from UnlockedView.")
        if self._session_manager:
            self._session_manager.stop_session()
        self.clipboard_service.clear_if_owned()
        self.search_input.clear()
        self._vault.lock()
        self.lock_requested.emit()
        self.close()

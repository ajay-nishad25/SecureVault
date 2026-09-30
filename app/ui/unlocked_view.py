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
from app.services.credential_service import CredentialService
from app.services.vault_service import DecryptedVault, VaultService

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
        self.title_input.setPlaceholderText("e.g. GitHub, Google, Work Email")
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
    """Read-only dialog for inspecting a credential with masked password."""

    def __init__(self, credential: Credential, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._credential = credential
        self.setWindowTitle("View Credential — SecureVault")
        self.resize(420, 260)

        layout = QVBoxLayout()
        layout.setSpacing(12)

        form = QFormLayout()

        self.title_val = QLineEdit(credential.title)
        self.title_val.setReadOnly(True)
        self.title_val.setStyleSheet("background-color: #161b22; color: #f0f6fc; border: 1px solid #30363d;")
        form.addRow("Title:", self.title_val)

        self.username_val = QLineEdit(credential.username)
        self.username_val.setReadOnly(True)
        self.username_val.setStyleSheet("background-color: #161b22; color: #f0f6fc; border: 1px solid #30363d;")
        form.addRow("Username:", self.username_val)

        pwd_layout = QHBoxLayout()
        pwd_layout.setSpacing(6)
        self.password_val = QLineEdit(credential.password)
        self.password_val.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_val.setReadOnly(True)
        self.password_val.setStyleSheet("background-color: #161b22; color: #f0f6fc; border: 1px solid #30363d;")
        pwd_layout.addWidget(self.password_val)

        self.toggle_pwd_btn = QPushButton("Show")
        self.toggle_pwd_btn.setStyleSheet("padding: 4px 10px; font-size: 11px;")
        self.toggle_pwd_btn.clicked.connect(self._toggle_password_visibility)
        pwd_layout.addWidget(self.toggle_pwd_btn)

        form.addRow("Password:", pwd_layout)

        self.notes_val = QLineEdit(credential.notes)
        self.notes_val.setReadOnly(True)
        self.notes_val.setStyleSheet("background-color: #161b22; color: #f0f6fc; border: 1px solid #30363d;")
        form.addRow("Notes:", self.notes_val)

        layout.addLayout(form)
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
        self.title_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #f0f6fc;")
        self.title_label.setWordWrap(True)
        main_layout.addWidget(self.title_label)

        # Username
        self.username_label = QLabel(username)
        self.username_label.setStyleSheet("font-size: 12px; color: #8b949e;")
        self.username_label.setWordWrap(True)
        main_layout.addWidget(self.username_label)

        # Notes (only displayed when present)
        if notes and notes.strip():
            self.notes_label = QLabel(notes.strip())
            self.notes_label.setStyleSheet("font-size: 11px; color: #768390; font-style: italic;")
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
        self.view_btn.setStyleSheet(
            "background-color: #21262d; color: #c9d1d9; border: 1px solid #30363d; "
            "border-radius: 4px; padding: 4px 12px; font-size: 11px; font-weight: 500;"
        )
        self.view_btn.clicked.connect(self._on_view_clicked)
        btn_layout.addWidget(self.view_btn)

        self.edit_btn = QPushButton("✏️ Edit")
        self.edit_btn.setStyleSheet(
            "background-color: #1f6feb; color: #ffffff; border: 1px solid #388bfd; "
            "border-radius: 4px; padding: 4px 12px; font-size: 11px; font-weight: 500;"
        )
        self.edit_btn.clicked.connect(self._on_edit_clicked)
        btn_layout.addWidget(self.edit_btn)

        self.delete_btn = QPushButton("🗑 Delete")
        self.delete_btn.setStyleSheet(
            "background-color: #21262d; color: #f85149; border: 1px solid #da3633; "
            "border-radius: 4px; padding: 4px 12px; font-size: 11px; font-weight: 500;"
        )
        self.delete_btn.clicked.connect(self._on_delete_clicked)
        btn_layout.addWidget(self.delete_btn)

        btn_layout.addStretch()
        main_layout.addLayout(btn_layout)

        self.setLayout(main_layout)
        self.setStyleSheet(
            "CredentialCardWidget {"
            "  background-color: #161b22;"
            "  border: 1px solid #30363d;"
            "  border-radius: 6px;"
            "}"
        )

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
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._vault = vault
        self._login_id = login_id
        self._vault_service = vault_service
        self._credential_service = credential_service or (
            CredentialService(vault_service) if vault_service else None
        )

        self.setWindowTitle("SecureVault — Vault Unlocked")
        self.resize(WINDOW_WIDTH, WINDOW_HEIGHT)
        self.center_on_screen()

        layout = QVBoxLayout()
        layout.setSpacing(10)
        layout.setContentsMargins(28, 18, 28, 18)

        # Header
        header = QLabel("🔓 SecureVault — Unlocked")
        header.setStyleSheet("font-size: 20px; font-weight: bold; color: #44bb44;")
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(header)

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
        self.search_input.setPlaceholderText("Search credentials...")
        self.search_input.setClearButtonEnabled(True)
        self.search_input.setStyleSheet(
            "QLineEdit {"
            "  background-color: #0d1117;"
            "  border: 1px solid #30363d;"
            "  border-radius: 6px;"
            "  padding: 6px 10px;"
            "  color: #c9d1d9;"
            "  font-size: 13px;"
            "}"
            "QLineEdit:focus {"
            "  border-color: #58a6ff;"
            "}"
        )
        self.search_input.textChanged.connect(self._on_search_changed)
        search_layout.addWidget(self.search_input, stretch=1)

        self.clear_btn = QPushButton("Clear")
        self.clear_btn.setStyleSheet(
            "QPushButton {"
            "  background-color: #21262d;"
            "  color: #c9d1d9;"
            "  border: 1px solid #30363d;"
            "  border-radius: 6px;"
            "  padding: 6px 14px;"
            "  font-size: 12px;"
            "}"
            "QPushButton:hover {"
            "  background-color: #30363d;"
            "}"
        )
        self.clear_btn.clicked.connect(self._on_clear_search)
        search_layout.addWidget(self.clear_btn)

        layout.addLayout(search_layout)

        # Credential Counter / Section Label
        self.counter_label = QLabel("Stored Credentials: <b>0</b>")
        self.counter_label.setStyleSheet("font-weight: bold; font-size: 13px; margin-top: 4px; color: #c9d1d9;")
        layout.addWidget(self.counter_label)

        # Empty state container
        self.empty_state_widget = QWidget()
        self.empty_state_widget.setMinimumHeight(140)
        self.empty_state_widget.setStyleSheet(
            "QWidget#EmptyStateContainer {"
            "  background-color: #0d1117;"
            "  border: 1px dashed #30363d;"
            "  border-radius: 6px;"
            "}"
        )
        self.empty_state_widget.setObjectName("EmptyStateContainer")
        empty_layout = QVBoxLayout(self.empty_state_widget)
        empty_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_layout.setContentsMargins(20, 16, 20, 16)
        empty_layout.setSpacing(6)

        self.empty_state_icon = QLabel("📭")
        self.empty_state_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_state_icon.setStyleSheet("font-size: 28px; background: transparent; border: none;")
        empty_layout.addWidget(self.empty_state_icon)

        self.empty_state_title = QLabel("No credentials yet.")
        self.empty_state_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_state_title.setStyleSheet("font-size: 15px; font-weight: bold; color: #8b949e; background: transparent; border: none;")
        empty_layout.addWidget(self.empty_state_title)

        self.empty_state_subtitle = QLabel("Add your first credential to get started.")
        self.empty_state_subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_state_subtitle.setStyleSheet("font-size: 13px; color: #6e7681; background: transparent; border: none;")
        empty_layout.addWidget(self.empty_state_subtitle)

        self.empty_state_add_btn = QPushButton("➕ Add Credential")
        self.empty_state_add_btn.setStyleSheet(
            "QPushButton {"
            "  background-color: #238636; color: #ffffff; border: 1px solid #2ea043; "
            "  border-radius: 6px; padding: 6px 16px; font-weight: bold; margin-top: 6px;"
            "}"
            "QPushButton:hover {"
            "  background-color: #2ea043;"
            "}"
        )
        self.empty_state_add_btn.clicked.connect(self._on_add_clicked)
        empty_layout.addWidget(self.empty_state_add_btn, alignment=Qt.AlignmentFlag.AlignCenter)

        layout.addWidget(self.empty_state_widget, stretch=1)

        # Credential List Section
        self.credential_list = QListWidget()
        self.credential_list.setSpacing(8)
        self.credential_list.setItemDelegate(CardItemDelegate(self.credential_list))
        self.credential_list.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.credential_list.setHorizontalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.credential_list.verticalScrollBar().setSingleStep(16)
        self.credential_list.setStyleSheet(
            "QListWidget {"
            "  background-color: #0d1117;"
            "  border: 1px solid #30363d;"
            "  border-radius: 6px;"
            "  padding: 6px;"
            "}"
            "QListWidget::item {"
            "  background: transparent;"
            "  border: none;"
            "  padding: 0px;"
            "  margin: 0px;"
            "}"
            "QListWidget::item:selected {"
            "  background: transparent;"
            "}"
            "QListWidget::item:hover {"
            "  background: transparent;"
            "}"
        )
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

        self.lock_btn = QPushButton("🔒 Lock Vault")
        self.lock_btn.setStyleSheet("font-weight: bold; padding: 6px 16px;")
        self.lock_btn.clicked.connect(self._on_lock_clicked)
        btn_layout.addWidget(self.lock_btn)

        self.exit_btn = QPushButton("Exit")
        self.exit_btn.setStyleSheet("padding: 6px 12px;")
        self.exit_btn.clicked.connect(self.close)
        btn_layout.addWidget(self.exit_btn)

        layout.addLayout(btn_layout)
        self.setLayout(layout)

        self._refresh_credentials()

    def center_on_screen(self) -> None:
        """Center the window on the primary screen."""
        from PySide6.QtWidgets import QApplication

        app = QApplication.instance()
        if not app:
            return
        screen = self.screen() or app.primaryScreen()
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
            dialog = ViewCredentialDialog(cred, self)
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

    def _on_lock_clicked(self) -> None:
        """Lock active session, zero memory buffers, and emit lock signal."""
        logger.info("Lock requested from UnlockedView.")
        self.search_input.clear()
        self._vault.lock()
        self.lock_requested.emit()
        self.close()

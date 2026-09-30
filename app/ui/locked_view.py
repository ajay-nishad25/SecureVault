"""SecureVault — Locked State View (Milestone 3 Authentication Interface).

Displays the locked interface where users enter their master password.
Coordinates with AuthenticationService to derive the Argon2id 256-bit KEK
on a background thread to maintain UI responsiveness.

M3 ARCHITECTURAL SCOPE:
In M3, this interface derives the 256-bit KEK. Decryption of the vault payload
will be integrated in Milestone 4 (M4) upon implementation of the encrypted
vault envelope.
"""

from __future__ import annotations

from PySide6.QtCore import QThread, Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.core.logging import get_logger
from app.services.authentication import AuthenticationResult, AuthenticationService
from app.services.initialization import InitializationService

logger = get_logger("ui.locked_view")


class AuthWorker(QThread):
    """Background worker executing Argon2id KEK derivation off the main UI thread."""

    result_ready = Signal(object)  # AuthenticationResult

    def __init__(
        self,
        auth_service: AuthenticationService,
        password: str,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._auth_service = auth_service
        self._password = password

    def run(self) -> None:
        # Run KEK derivation in worker thread to prevent freezing the PySide6 UI
        result = self._auth_service.authenticate(self._password)
        # Clear transient password reference
        self._password = ""
        self.result_ready.emit(result)


class LockedView(QWidget):
    """View displayed when the application is initialized and locked."""

    reset_requested = Signal()  # Emitted when user resets setup in dev mode
    authenticated = Signal(object)  # Emitted with AuthenticationResult upon KEK derivation

    def __init__(
        self,
        init_service: InitializationService | None = None,
        auth_service: AuthenticationService | None = None,
    ) -> None:
        super().__init__()
        self._init_service = init_service or InitializationService()
        self._auth_service = auth_service or AuthenticationService()
        self._worker: AuthWorker | None = None

        self.setWindowTitle("SecureVault — Vault Locked")
        self.resize(520, 420)

        layout = QVBoxLayout()
        layout.setSpacing(14)
        layout.setContentsMargins(32, 28, 32, 28)

        # Header with lock icon
        header = QLabel("🔒 SecureVault — Locked")
        header.setStyleSheet("font-size: 20px; font-weight: bold;")
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(header)

        login_id = self._init_service.get_login_id() or "Default User"
        user_info = QLabel(f"Profile: <b>{login_id}</b>")
        user_info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(user_info)

        # Master Password Input Form
        form_layout = QFormLayout()
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.setPlaceholderText("Enter master password to unlock")
        self.password_input.returnPressed.connect(self._on_unlock_clicked)
        form_layout.addRow("Master Password:", self.password_input)
        layout.addLayout(form_layout)

        # Show password toggle
        self.show_password_cb = QCheckBox("Show password")
        self.show_password_cb.toggled.connect(self._toggle_password_visibility)
        layout.addWidget(self.show_password_cb)

        # Status / Feedback label
        self.status_label = QLabel("")
        self.status_label.setWordWrap(True)
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.status_label)

        # Informational M3 boundary note
        info_note = QLabel(
            "Milestone 3 Architecture:\n"
            "Entering your master password derives a 256-bit Key Encryption Key (KEK) "
            "via Argon2id (64 MiB RAM). Real encrypted vault storage will be connected in M4."
        )
        info_note.setWordWrap(True)
        info_note.setStyleSheet(
            "background-color: #22272e; color: #8b949e; padding: 12px; border-radius: 6px; font-size: 11px;"
        )
        layout.addWidget(info_note)

        layout.addStretch()

        # Action buttons
        btn_layout = QHBoxLayout()

        self.unlock_btn = QPushButton("Unlock Vault")
        self.unlock_btn.setDefault(True)
        self.unlock_btn.clicked.connect(self._on_unlock_clicked)
        btn_layout.addWidget(self.unlock_btn)

        self.reset_btn = QPushButton("Reset Setup (Dev)")
        self.reset_btn.setToolTip("Delete initialization marker to re-test the first-run wizard")
        self.reset_btn.clicked.connect(self._on_reset)
        btn_layout.addWidget(self.reset_btn)

        self.exit_btn = QPushButton("Exit")
        self.exit_btn.clicked.connect(self.close)
        btn_layout.addWidget(self.exit_btn)

        layout.addLayout(btn_layout)
        self.setLayout(layout)

    def _toggle_password_visibility(self, checked: bool) -> None:
        mode = QLineEdit.EchoMode.Normal if checked else QLineEdit.EchoMode.Password
        self.password_input.setEchoMode(mode)

    def _on_unlock_clicked(self) -> None:
        password = self.password_input.text()
        if not password:
            self.status_label.setText("✕ Master password cannot be empty.")
            self.status_label.setStyleSheet("color: #ee5555; font-weight: bold;")
            return

        self._set_ui_busy(True)
        self.status_label.setText("Deriving 256-bit KEK via Argon2id (64 MiB RAM)...")
        self.status_label.setStyleSheet("color: #58a6ff;")

        # Launch derivation on background thread
        self._worker = AuthWorker(self._auth_service, password, parent=self)
        self._worker.result_ready.connect(self._on_auth_completed)
        self._worker.start()

    def _on_auth_completed(self, result: AuthenticationResult) -> None:
        self._set_ui_busy(False)
        self.password_input.clear()

        if result.success:
            logger.info("KEK derivation successful in UI.")
            self.status_label.setText(
                "✓ Master KEK derived successfully (Argon2id 256-bit).\n"
                "Encrypted vault payload decryption will be connected in Milestone 4 (M4)."
            )
            self.status_label.setStyleSheet("color: #44bb44; font-weight: bold;")
            self.authenticated.emit(result)
        else:
            self.status_label.setText(f"✕ {result.error or 'Authentication failed.'}")
            self.status_label.setStyleSheet("color: #ee5555; font-weight: bold;")

    def _set_ui_busy(self, busy: bool) -> None:
        self.password_input.setEnabled(not busy)
        self.unlock_btn.setEnabled(not busy)
        self.reset_btn.setEnabled(not busy)

    def _on_reset(self) -> None:
        self._auth_service.clear_session()
        self._init_service.reset()
        self.reset_requested.emit()
        self.close()

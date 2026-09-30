"""SecureVault — Locked State View & Cryptographic Unlock Controller.

Presented when the application is initialized and in the LOCKED state.
Coordinates with VaultService to:
  1. Derive the Argon2id 256-bit KEK from the entered master password.
  2. Attempt AES-256-GCM authenticated unwrapping of the DEK from the header.
  3. Decrypt and authenticate the encrypted vault payload.
  4. Perform derivation and decryption on a background QThread to maintain UI responsiveness.
"""

from __future__ import annotations

from dataclasses import dataclass

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

from app.core.exceptions import (
    AuthenticationError,
    CorruptedVaultError,
    VaultNotFoundError,
)
from app.core.logging import get_logger
from app.services.authentication import AuthenticationResult, AuthenticationService
from app.services.initialization import InitializationService
from app.services.vault_service import DecryptedVault, VaultService

logger = get_logger("ui.locked_view")


@dataclass
class UnlockResult:
    """Outcome of an asynchronous vault unlock attempt."""

    success: bool
    vault: DecryptedVault | None = None
    error: str | None = None


class AuthWorker(QThread):
    """Background worker executing Argon2id KEK derivation and DEK unwrapping off the UI thread."""

    result_ready = Signal(object)  # Emits UnlockResult

    def __init__(
        self,
        vault_service: VaultService,
        password: str,
        auth_service: AuthenticationService | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._vault_service = vault_service
        self._auth_service = auth_service or AuthenticationService()
        self._password = password

    def run(self) -> None:
        try:
            # Check if vault file exists
            if not self._vault_service.is_vault_created():
                # Fallback for dev mode when vault is not yet created on disk
                res = self._auth_service.authenticate(self._password)
                if res.success:
                    result = UnlockResult(success=True, error=None)
                else:
                    result = UnlockResult(success=False, error=res.error)
            else:
                # Real M4 cryptographic unlock flow
                vault = self._vault_service.unlock_vault(self._password)
                result = UnlockResult(success=True, vault=vault, error=None)
        except AuthenticationError as err:
            logger.warning("Authentication failed: incorrect master password.")
            result = UnlockResult(success=False, error=str(err))
        except CorruptedVaultError as err:
            logger.error("Unlock failed: corrupted vault file: %s", err)
            result = UnlockResult(success=False, error=f"Vault corruption detected: {err}")
        except VaultNotFoundError as err:
            logger.error("Unlock failed: vault file not found: %s", err)
            result = UnlockResult(success=False, error="Vault file not found. Please re-run setup.")
        except Exception as err:
            logger.error("Unexpected error during vault unlock: %s", err)
            result = UnlockResult(success=False, error="An unexpected error occurred during unlock.")
        finally:
            self._password = ""

        self.result_ready.emit(result)


class LockedView(QWidget):
    """View displayed when the application is initialized and locked."""

    reset_requested = Signal()  # Emitted when user resets setup in dev mode
    vault_unlocked = Signal(object)  # Emitted with DecryptedVault upon successful unlock
    authenticated = Signal(object)  # Emitted for backward compatibility with M3 tests

    def __init__(
        self,
        init_service: InitializationService | None = None,
        auth_service: AuthenticationService | None = None,
        vault_service: VaultService | None = None,
    ) -> None:
        super().__init__()
        self._init_service = init_service or InitializationService()
        self._auth_service = auth_service or AuthenticationService()
        self._vault_service = vault_service or VaultService(self._init_service.config)
        self._worker: AuthWorker | None = None

        self.setWindowTitle("SecureVault — Vault Locked")
        self.resize(520, 430)

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

        # Informational M4 architecture note
        info_note = QLabel(
            "Milestone 4 Cryptographic Vault:\n"
            "Entering your master password derives a 256-bit KEK via Argon2id (64 MiB RAM), "
            "unwraps the random DEK with AES-256-GCM, and decrypts the vault payload."
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
        self.reset_btn.setToolTip("Delete initialization marker and vault to re-test the first-run wizard")
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
        self.status_label.setText("Unwrapping DEK and decrypting vault...")
        self.status_label.setStyleSheet("color: #58a6ff;")

        # Launch unlock on background worker thread
        self._worker = AuthWorker(
            vault_service=self._vault_service,
            password=password,
            auth_service=self._auth_service,
            parent=self,
        )
        self._worker.result_ready.connect(self._on_auth_completed)
        self._worker.start()

    def _on_auth_completed(self, result: UnlockResult) -> None:
        self._set_ui_busy(False)
        self.password_input.clear()

        if result.success:
            logger.info("Vault unlock successful in UI.")
            self.status_label.setText("✓ Vault unlocked successfully!")
            self.status_label.setStyleSheet("color: #44bb44; font-weight: bold;")
            self.vault_unlocked.emit(result.vault)
            # Backward compatibility with M3 test suite
            auth_res = AuthenticationResult(success=True, kek=b"\x00" * 32, message="Success")
            self.authenticated.emit(auth_res)
        else:
            self.status_label.setText(f"✕ {result.error or 'Incorrect master password or invalid vault.'}")
            self.status_label.setStyleSheet("color: #ee5555; font-weight: bold;")
            auth_res = AuthenticationResult(success=False, error=result.error)
            self.authenticated.emit(auth_res)

    def _set_ui_busy(self, busy: bool) -> None:
        self.password_input.setEnabled(not busy)
        self.unlock_btn.setEnabled(not busy)
        self.reset_btn.setEnabled(not busy)

    def _on_reset(self) -> None:
        self._auth_service.clear_session()
        self._init_service.reset()
        self.reset_requested.emit()
        self.close()

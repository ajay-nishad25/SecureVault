"""SecureVault — Unlocked Vault Placeholder View.

Displayed upon successful cryptographic unlock in Milestone 4 (M4).
Provides vault session metadata and a lock action to clear in-memory key material.
Full credential management (CRUD, search, generator) will be integrated in Milestone 5 (M5).
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.core.logging import get_logger
from app.services.vault_service import DecryptedVault

logger = get_logger("ui.unlocked_view")


class UnlockedView(QWidget):
    """View displayed when the vault is unlocked in Milestone 4."""

    lock_requested = Signal()  # Emitted when user clicks 'Lock Vault'

    def __init__(
        self,
        vault: DecryptedVault,
        login_id: str = "Default User",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._vault = vault
        self._login_id = login_id

        self.setWindowTitle("SecureVault — Vault Unlocked")
        self.resize(540, 420)

        layout = QVBoxLayout()
        layout.setSpacing(16)
        layout.setContentsMargins(32, 28, 32, 28)

        # Header
        header = QLabel("🔓 SecureVault — Unlocked")
        header.setStyleSheet("font-size: 20px; font-weight: bold; color: #44bb44;")
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(header)

        # Profile & Vault Info
        user_info = QLabel(f"Profile: <b>{self._login_id}</b>")
        user_info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(user_info)

        vault_meta = QLabel(
            f"Vault ID: <code>{self._vault.vault_id}</code><br>"
            f"Stored Credentials: <b>{self._vault.item_count}</b>"
        )
        vault_meta.setAlignment(Qt.AlignmentFlag.AlignCenter)
        vault_meta.setStyleSheet("color: #adbac7;")
        layout.addWidget(vault_meta)

        # Information Card
        status_box = QLabel(
            "<b>Milestone 4 — Cryptographic Vault Active</b><br><br>"
            "✓ Master password verified via authenticated DEK unwrapping.<br>"
            "✓ AES-256-GCM payload successfully authenticated and decrypted.<br><br>"
            "<i>Note: Credential list, CRUD operations, search, and the password generator "
            "will be implemented in Milestone 5 (M5).</i>"
        )
        status_box.setWordWrap(True)
        status_box.setStyleSheet(
            "background-color: #22272e; color: #adbac7; padding: 16px; border-radius: 6px; border: 1px solid #444c56;"
        )
        layout.addWidget(status_box)

        layout.addStretch()

        # Action Buttons
        btn_layout = QHBoxLayout()

        self.lock_btn = QPushButton("🔒 Lock Vault")
        self.lock_btn.setStyleSheet("font-weight: bold; padding: 6px 16px;")
        self.lock_btn.clicked.connect(self._on_lock_clicked)
        btn_layout.addWidget(self.lock_btn)

        self.exit_btn = QPushButton("Exit")
        self.exit_btn.clicked.connect(self.close)
        btn_layout.addWidget(self.exit_btn)

        layout.addLayout(btn_layout)
        self.setLayout(layout)

    def _on_lock_clicked(self) -> None:
        """Lock active session, zero memory buffers, and emit lock signal."""
        logger.info("Lock requested from UnlockedView.")
        self._vault.lock()
        self.lock_requested.emit()
        self.close()

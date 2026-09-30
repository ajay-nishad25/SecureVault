"""SecureVault — Locked State View (Placeholder for M3 Authentication).

Displays the locked state interface when the application is initialized.
In Milestone 3 (M3), this placeholder will be upgraded to the full
Login / Unlock authentication screen.
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

from app.services.initialization import InitializationService


class LockedView(QWidget):
    """View displayed when the application is initialized and locked."""

    reset_requested = Signal()  # Emitted when user resets setup in dev mode

    def __init__(self, init_service: InitializationService | None = None) -> None:
        super().__init__()
        self._init_service = init_service or InitializationService()

        self.setWindowTitle("SecureVault — Vault Locked")
        self.resize(520, 360)

        layout = QVBoxLayout()
        layout.setSpacing(16)
        layout.setContentsMargins(32, 32, 32, 32)

        # Header with lock icon
        header = QLabel("🔒 SecureVault — Locked")
        header.setStyleSheet("font-size: 20px; font-weight: bold;")
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(header)

        login_id = self._init_service.get_login_id() or "Unknown User"
        user_info = QLabel(f"Profile: <b>{login_id}</b>")
        user_info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(user_info)

        status_box = QLabel(
            "State: LOCKED\n\n"
            "This application has completed first-run setup. In Milestone 3 (M3), "
            "this screen will provide the master-password unlock interface.\n\n"
            "To test the first-run wizard again, you may click 'Reset Setup (Dev)'."
        )
        status_box.setWordWrap(True)
        status_box.setStyleSheet(
            "background-color: #22272e; color: #adbac7; padding: 16px; border-radius: 6px; border: 1px solid #444c56;"
        )
        layout.addWidget(status_box)

        layout.addStretch()

        # Action buttons
        btn_layout = QHBoxLayout()

        self.reset_btn = QPushButton("Reset Setup (Dev)")
        self.reset_btn.setToolTip("Delete initialization marker to re-test the first-run wizard")
        self.reset_btn.clicked.connect(self._on_reset)
        btn_layout.addWidget(self.reset_btn)

        self.exit_btn = QPushButton("Exit Application")
        self.exit_btn.clicked.connect(self.close)
        btn_layout.addWidget(self.exit_btn)

        layout.addLayout(btn_layout)
        self.setLayout(layout)

    def _on_reset(self) -> None:
        self._init_service.reset()
        self.reset_requested.emit()
        self.close()

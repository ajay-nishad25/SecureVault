"""SecureVault — Centralized Clipboard Security Service (Milestone M10).

Responsible for:
- Copying username and password credential fields to the OS clipboard.
- Automatic 30-second clipboard cleanup timer.
- Strict clipboard ownership verification (only clears exact value SecureVault placed).
- Prevention of clearing user-replaced clipboard content.
- Immediate ownership-aware cleanup upon vault session lock or application exit.
- Zero clipboard history or persistence; zero sensitive value logging.
"""

from __future__ import annotations

from typing import Any
from PySide6.QtCore import QObject, QTimer, Signal
from PySide6.QtGui import QClipboard
from PySide6.QtWidgets import QApplication

from app.core.logging import get_logger

logger = get_logger("services.clipboard_service")

CLIPBOARD_CLEAR_TIMEOUT_SECONDS: int = 30


class ClipboardService(QObject):
    """Centralized service managing secure clipboard copies and auto-cleanup."""

    # Signals (emitted without sensitive payload)
    copied = Signal(str)  # field_name: "username", "password", or generic
    cleared = Signal()    # emitted when SecureVault clears the clipboard

    _instance: ClipboardService | None = None

    def __init__(
        self,
        timeout_seconds: int | float = CLIPBOARD_CLEAR_TIMEOUT_SECONDS,
        clipboard: Any = None,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._timeout_seconds = timeout_seconds
        self._custom_clipboard = clipboard
        self._tracked_value: str | None = None

        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._on_timeout)

    @classmethod
    def instance(cls) -> ClipboardService:
        """Access global shared singleton instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        """Reset global shared singleton instance (primarily for test teardown)."""
        if cls._instance is not None:
            cls._instance.cancel()
            cls._instance = None

    @property
    def timeout_seconds(self) -> int | float:
        """Configured auto-clear timeout in seconds."""
        return self._timeout_seconds

    def _get_clipboard(self) -> QClipboard | Any | None:
        if self._custom_clipboard is not None:
            return self._custom_clipboard
        app = QApplication.instance()
        if app is not None:
            return app.clipboard()
        return None

    def _get_clipboard_text(self) -> str:
        cb = self._get_clipboard()
        if cb is not None:
            try:
                return cb.text() or ""
            except Exception as err:
                logger.error("Failed to read clipboard text: %s", err)
        return ""

    def _set_clipboard_text(self, text: str) -> None:
        cb = self._get_clipboard()
        if cb is not None:
            try:
                cb.setText(text)
            except Exception as err:
                logger.error("Failed to set clipboard text: %s", err)

    def _clear_clipboard_os(self) -> None:
        cb = self._get_clipboard()
        if cb is not None:
            try:
                cb.clear()
            except Exception as err:
                logger.error("Failed to clear OS clipboard: %s", err)

    def copy_text(self, text: str, field_name: str = "") -> bool:
        """Copy a non-empty text value to the clipboard and arm the 30-second cleanup timer."""
        if not isinstance(text, str) or not text.strip():
            logger.warning("Rejected clipboard copy of empty or non-string value.")
            return False

        # Stop existing timer (overlapping copy cancels previous cleanup)
        self._timer.stop()

        # Place on OS clipboard
        self._set_clipboard_text(text)
        self._tracked_value = text

        # Arm single-shot 30-second auto-clear timer
        timeout_ms = int(self._timeout_seconds * 1000)
        self._timer.start(timeout_ms)

        logger.info("SecureVault clipboard copy initiated")
        self.copied.emit(field_name)
        return True

    def copy_username(self, username: str) -> bool:
        """Copy username/login ID to clipboard and arm cleanup timer."""
        return self.copy_text(username, field_name="username")

    def copy_password(self, password: str) -> bool:
        """Copy credential password to clipboard and arm cleanup timer."""
        return self.copy_text(password, field_name="password")

    def _on_timeout(self) -> bool:
        """Timer callback: clear clipboard if and only if SecureVault still owns the content."""
        current_text = self._get_clipboard_text()
        cleared = False
        if self._tracked_value is not None and current_text == self._tracked_value:
            self._clear_clipboard_os()
            logger.info("SecureVault clipboard cleanup completed")
            self.cleared.emit()
            cleared = True
        else:
            logger.info("SecureVault clipboard cleanup skipped (content replaced or cleared)")

        # Clear tracked value and ensure timer is stopped
        self._tracked_value = None
        self._timer.stop()
        return cleared

    def clear_if_owned(self) -> bool:
        """Immediate cleanup invoked when vault locks or application exits.

        Clears clipboard only if the currently tracked SecureVault value is still present.
        """
        self._timer.stop()
        current_text = self._get_clipboard_text()
        cleared = False
        if self._tracked_value is not None and current_text == self._tracked_value:
            self._clear_clipboard_os()
            logger.info("SecureVault clipboard cleanup completed")
            self.cleared.emit()
            cleared = True

        self._tracked_value = None
        return cleared

    def cancel(self) -> None:
        """Cancel cleanup timer and discard tracking state without modifying clipboard."""
        self._timer.stop()
        self._tracked_value = None

    def is_tracking(self) -> bool:
        """Check if an active cleanup timer is currently running."""
        return self._tracked_value is not None and self._timer.isActive()

    def has_ownership(self) -> bool:
        """Check if OS clipboard currently contains the exact value SecureVault placed."""
        return self._tracked_value is not None and self._get_clipboard_text() == self._tracked_value

    def get_tracked_value(self) -> str | None:
        """Return currently tracked value for testing verification."""
        return self._tracked_value

"""Tests for Centralized ClipboardService (Milestone M10).

Verifies:
- Copy username and password to clipboard.
- 30-second auto-clear timer functionality.
- Strict clipboard ownership verification.
- Replaced clipboard content is preserved (never cleared).
- Overlapping copy operations cancel previous timer and track latest value.
- Safe handling of empty or invalid copy requests.
- Vault session lock clears owned clipboard content while preserving user content.
- Application exit cleanup.
- Zero sensitive data in logs, no persistence, no clipboard history.
"""

from __future__ import annotations

import logging
import os
import sys
from typing import Any
import pytest
from PySide6.QtCore import QObject
from PySide6.QtWidgets import QApplication

os.environ["QT_QPA_PLATFORM"] = "offscreen"


@pytest.fixture(scope="session")
def qapp() -> QApplication:
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    return app


from app.core.config import AppConfig
from app.services.clipboard_service import (
    CLIPBOARD_CLEAR_TIMEOUT_SECONDS,
    ClipboardService,
)


class MockClipboard:
    """Mock clipboard for deterministic in-memory testing without OS dependencies."""

    def __init__(self, initial_text: str = "") -> None:
        self._text = initial_text

    def text(self) -> str:
        return self._text

    def setText(self, text: str) -> None:
        self._text = text

    def clear(self) -> None:
        self._text = ""


@pytest.fixture(autouse=True)
def reset_clipboard_service():
    """Ensure ClipboardService singleton is reset before and after each test."""
    ClipboardService.reset_instance()
    yield
    ClipboardService.reset_instance()


# =============================================================================
# 1. USERNAME & PASSWORD COPY WITH AUTO-CLEAR
# =============================================================================

def test_copy_username_reaches_clipboard_and_cleans_up(qapp: QApplication) -> None:
    """Verify username reaches clipboard, emits signal, and clears after timeout."""
    mock_cb = MockClipboard()
    service = ClipboardService(timeout_seconds=0.1, clipboard=mock_cb)

    signal_received = []
    cleared_received = []
    service.copied.connect(lambda f: signal_received.append(f))
    service.cleared.connect(lambda: cleared_received.append(True))

    assert service.copy_username("alice_vault_user") is True
    assert mock_cb.text() == "alice_vault_user"
    assert service.get_tracked_value() == "alice_vault_user"
    assert service.has_ownership() is True
    assert signal_received == ["username"]

    # Trigger timeout cleanup
    assert service._on_timeout() is True
    assert mock_cb.text() == ""
    assert service.get_tracked_value() is None
    assert service.has_ownership() is False
    assert len(cleared_received) == 1


def test_copy_password_reaches_clipboard_and_cleans_up(qapp: QApplication) -> None:
    """Verify password reaches clipboard and clears on timeout."""
    mock_cb = MockClipboard()
    service = ClipboardService(timeout_seconds=0.1, clipboard=mock_cb)

    signal_received = []
    cleared_received = []
    service.copied.connect(lambda f: signal_received.append(f))
    service.cleared.connect(lambda: cleared_received.append(True))

    assert service.copy_password("SuperSecretP@ss123!") is True
    assert mock_cb.text() == "SuperSecretP@ss123!"
    assert service.get_tracked_value() == "SuperSecretP@ss123!"
    assert service.has_ownership() is True
    assert signal_received == ["password"]

    # Timeout clears exact password
    assert service._on_timeout() is True
    assert mock_cb.text() == ""
    assert service.get_tracked_value() is None
    assert len(cleared_received) == 1


# =============================================================================
# 2. CLIPBOARD OWNERSHIP PROTECTION
# =============================================================================

def test_clipboard_ownership_protection_user_replacement(qapp: QApplication) -> None:
    """Verify that if the user replaces clipboard content before timeout,

    SecureVault's cleanup does NOT clear the user's new clipboard content.
    """
    mock_cb = MockClipboard()
    service = ClipboardService(timeout_seconds=0.1, clipboard=mock_cb)

    service.copy_password("vault_secret_password")
    assert mock_cb.text() == "vault_secret_password"

    # User replaces clipboard with unrelated content
    mock_cb.setText("hello world, my custom notes")
    assert service.has_ownership() is False

    # Timer expires
    cleared = service._on_timeout()
    assert cleared is False

    # The user's new clipboard value MUST remain untouched
    assert mock_cb.text() == "hello world, my custom notes"
    assert service.get_tracked_value() is None


def test_clipboard_ownership_already_cleared(qapp: QApplication) -> None:
    """Verify that if clipboard is already empty when timeout fires, no error occurs."""
    mock_cb = MockClipboard()
    service = ClipboardService(timeout_seconds=0.1, clipboard=mock_cb)

    service.copy_username("admin_user")
    mock_cb.clear()

    cleared = service._on_timeout()
    assert cleared is False
    assert mock_cb.text() == ""
    assert service.get_tracked_value() is None


# =============================================================================
# 3. OVERLAPPING COPY OPERATIONS
# =============================================================================

def test_overlapping_copies_username_then_password(qapp: QApplication) -> None:
    """Verify Copy Username followed by Copy Password before timeout cancels

    the old timer and tracks the password.
    """
    mock_cb = MockClipboard()
    service = ClipboardService(timeout_seconds=0.1, clipboard=mock_cb)

    # 1. Copy Username
    service.copy_username("initial_username")
    assert mock_cb.text() == "initial_username"
    assert service.get_tracked_value() == "initial_username"

    # 2. Copy Password before timeout
    service.copy_password("second_secret_password")
    assert mock_cb.text() == "second_secret_password"
    assert service.get_tracked_value() == "second_secret_password"

    # 3. Timeout fires for the second copy: clears password
    assert service._on_timeout() is True
    assert mock_cb.text() == ""
    assert service.get_tracked_value() is None


def test_overlapping_copies_password_then_username(qapp: QApplication) -> None:
    """Verify Copy Password followed by Copy Username before timeout cancels

    the old timer and tracks the username.
    """
    mock_cb = MockClipboard()
    service = ClipboardService(timeout_seconds=0.1, clipboard=mock_cb)

    # 1. Copy Password
    service.copy_password("first_secret_pass")
    assert mock_cb.text() == "first_secret_pass"

    # 2. Copy Username before timeout
    service.copy_username("second_username")
    assert mock_cb.text() == "second_username"
    assert service.get_tracked_value() == "second_username"

    # 3. Timeout clears username
    assert service._on_timeout() is True
    assert mock_cb.text() == ""


def test_overlapping_identical_copy_restarts_timer(qapp: QApplication) -> None:
    """Verify copying the exact same value re-arms the cleanup timer."""
    mock_cb = MockClipboard()
    service = ClipboardService(timeout_seconds=0.1, clipboard=mock_cb)

    service.copy_username("same_user")
    assert service._timer.isActive() is True

    # Copy same username again
    service.copy_username("same_user")
    assert service._timer.isActive() is True
    assert mock_cb.text() == "same_user"
    assert service.get_tracked_value() == "same_user"


# =============================================================================
# 4. EMPTY AND INVALID VALUES
# =============================================================================

def test_empty_and_whitespace_values_rejected(qapp: QApplication) -> None:
    """Verify empty strings and whitespace are rejected without modifying clipboard."""
    mock_cb = MockClipboard(initial_text="pre_existing_data")
    service = ClipboardService(timeout_seconds=0.1, clipboard=mock_cb)

    assert service.copy_text("") is False
    assert service.copy_username("") is False
    assert service.copy_password("   ") is False
    assert service.copy_text(None) is False  # type: ignore

    # Clipboard must remain unchanged
    assert mock_cb.text() == "pre_existing_data"
    assert service.get_tracked_value() is None
    assert service.is_tracking() is False


# =============================================================================
# 5. LOCK & APPLICATION EXIT INTEGRATION
# =============================================================================

def test_lock_clears_owned_clipboard_value(qapp: QApplication) -> None:
    """Verify clear_if_owned() cleans up clipboard when SecureVault value is present."""
    mock_cb = MockClipboard()
    service = ClipboardService(timeout_seconds=30, clipboard=mock_cb)

    service.copy_password("active_vault_password")
    assert service.is_tracking() is True
    assert mock_cb.text() == "active_vault_password"

    # Vault session locks
    cleared = service.clear_if_owned()
    assert cleared is True
    assert mock_cb.text() == ""
    assert service.get_tracked_value() is None
    assert service.is_tracking() is False


def test_lock_preserves_user_replaced_clipboard_value(qapp: QApplication) -> None:
    """Verify clear_if_owned() does NOT clear clipboard if user copied external text."""
    mock_cb = MockClipboard()
    service = ClipboardService(timeout_seconds=30, clipboard=mock_cb)

    service.copy_password("active_vault_password")

    # User replaces clipboard with external text
    mock_cb.setText("external document content")

    # Vault session locks
    cleared = service.clear_if_owned()
    assert cleared is False

    # External text must remain intact
    assert mock_cb.text() == "external document content"
    assert service.get_tracked_value() is None
    assert service.is_tracking() is False


def test_cancel_disarms_timer_without_modifying_clipboard(qapp: QApplication) -> None:
    """Verify cancel() stops timer and resets state without clearing clipboard."""
    mock_cb = MockClipboard()
    service = ClipboardService(timeout_seconds=30, clipboard=mock_cb)

    service.copy_username("temp_user")
    assert service.is_tracking() is True

    service.cancel()
    assert service.is_tracking() is False
    assert service.get_tracked_value() is None
    assert mock_cb.text() == "temp_user"


# =============================================================================
# 6. SECURITY & ZERO SENSITIVE DATA IN LOGS / SETTINGS
# =============================================================================

def test_no_sensitive_values_in_logs(qapp: QApplication, caplog: pytest.LogCaptureFixture) -> None:
    """Verify that neither username, password, nor clipboard contents are logged."""
    caplog.set_level(logging.DEBUG)
    mock_cb = MockClipboard()
    service = ClipboardService(timeout_seconds=0.1, clipboard=mock_cb)

    secret_username = "super_private_alice"
    secret_password = "CriticalVaultSecret987!!"

    service.copy_username(secret_username)
    service.copy_password(secret_password)
    service._on_timeout()

    all_logs = caplog.text

    # Assert secret values are strictly absent from logs
    assert secret_username not in all_logs
    assert secret_password not in all_logs

    # Assert operational non-sensitive logs are present
    assert "SecureVault clipboard copy initiated" in all_logs
    assert "SecureVault clipboard cleanup completed" in all_logs


def test_clipboard_timeout_constant() -> None:
    """Verify system-defined 30-second constant."""
    assert CLIPBOARD_CLEAR_TIMEOUT_SECONDS == 30
    service = ClipboardService()
    assert service.timeout_seconds == 30


# =============================================================================
# 7. REAL QT CLIPBOARD INTEGRATION
# =============================================================================

def test_real_qt_clipboard_copy_and_timeout(qapp: QApplication) -> None:
    """Verify operations against the live QApplication.clipboard()."""
    qt_cb = qapp.clipboard()
    qt_cb.clear()

    service = ClipboardService(timeout_seconds=0.1)
    assert service.copy_password("RealQtSecretPass123!") is True
    assert qt_cb.text() == "RealQtSecretPass123!"

    # Simulate timeout
    assert service._on_timeout() is True
    assert qt_cb.text() == ""


def test_real_qt_clipboard_ownership_replacement(qapp: QApplication) -> None:
    """Verify real QApplication.clipboard() ownership checks when replaced."""
    qt_cb = qapp.clipboard()
    qt_cb.clear()

    service = ClipboardService(timeout_seconds=0.1)
    service.copy_username("qt_user")
    assert qt_cb.text() == "qt_user"

    # User replaces with external clipboard text
    qt_cb.setText("external user text")

    # Timeout should skip clearing
    assert service._on_timeout() is False
    assert qt_cb.text() == "external user text"


def test_no_clipboard_data_in_settings(tmp_path, qapp: QApplication) -> None:
    """Verify clipboard content is never persisted to settings.json."""
    from app.services.settings_service import SettingsService
    config = AppConfig(data_dir=tmp_path)
    settings_service = SettingsService(config)

    service = ClipboardService(timeout_seconds=30)
    service.copy_password("TransientPassword999!")

    # Verify settings file does not contain password
    settings_file = config.settings_path
    if settings_file.exists():
        content = settings_file.read_text(encoding="utf-8")
        assert "TransientPassword999!" not in content
    settings = settings_service.get_settings()
    assert not hasattr(settings, "clipboard")

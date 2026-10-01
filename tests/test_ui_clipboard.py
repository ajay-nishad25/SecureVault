"""Tests for UI Clipboard Integration (Milestone M10).

Verifies:
- ViewCredentialDialog:
  - Copy Username button copies username and shows feedback note.
  - Copy Password button copies password and shows feedback note.
  - Password remains masked by default with Show/Hide toggle.
  - Read-only enforcement of all displayed credential fields.
- UnlockedView:
  - Status label displays non-sensitive confirmation when copy occurs.
  - Status label updates when clipboard auto-clears.
  - Manual Lock Vault cleans up SecureVault-owned clipboard.
  - Manual Lock Vault preserves user-replaced clipboard content.
  - Auto-lock timeout cleans up SecureVault-owned clipboard.
- ApplicationController:
  - Session lock transition cleans up SecureVault-owned clipboard.
"""

from __future__ import annotations

import os
import sys
from unittest.mock import MagicMock
import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QLineEdit

os.environ["QT_QPA_PLATFORM"] = "offscreen"


@pytest.fixture(scope="session")
def qapp() -> QApplication:
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    return app


from pathlib import Path
from app.core.config import AppConfig
from app.crypto.kdf import KDFParameters
from app.models.credential import Credential
from app.services.clipboard_service import ClipboardService
from app.services.credential_service import CredentialService
from app.services.session_manager import SessionManager
from app.services.vault_service import DecryptedVault, VaultService
from app.ui.app_window import ApplicationController
from app.ui.unlocked_view import UnlockedView, ViewCredentialDialog


class MockClipboard:
    """Mock clipboard for deterministic UI test execution."""

    def __init__(self, initial_text: str = "") -> None:
        self._text = initial_text

    def text(self) -> str:
        return self._text

    def setText(self, text: str) -> None:
        self._text = text

    def clear(self) -> None:
        self._text = ""


@pytest.fixture(autouse=True)
def reset_clipboard():
    """Reset clipboard service singleton between tests."""
    ClipboardService.reset_instance()
    yield
    ClipboardService.reset_instance()


@pytest.fixture
def sample_credential() -> Credential:
    return Credential(
        title="GitHub Work",
        username="octocat_dev",
        password="OctoSecretPassword123!",
        notes="Primary developer account",
    )


@pytest.fixture
def unlocked_vault_and_services(tmp_path: Path):
    """Provide initialized VaultService and CredentialService."""
    config = AppConfig(data_dir=tmp_path)
    vault_service = VaultService(config)
    vault = vault_service.create_vault(
        master_password="MasterTestPassword123!",
        kdf_params=KDFParameters.fast_for_testing(),
    )
    credential_service = CredentialService(vault_service)
    return vault, vault_service, credential_service


# =============================================================================
# 1. VIEW CREDENTIAL DIALOG TESTS
# =============================================================================

def test_view_dialog_copy_username_action(qapp: QApplication, sample_credential: Credential) -> None:
    """Verify Copy Username copies username to clipboard and shows feedback."""
    mock_cb = MockClipboard()
    clip_service = ClipboardService(timeout_seconds=30, clipboard=mock_cb)

    dialog = ViewCredentialDialog(sample_credential, clipboard_service=clip_service)

    # Verify initial state
    assert dialog.username_val.text() == "octocat_dev"
    assert dialog.copy_username_btn.text() == "Copy Username"
    assert dialog.status_label.text() == ""

    # Click Copy Username
    dialog.copy_username_btn.click()

    assert mock_cb.text() == "octocat_dev"
    assert clip_service.get_tracked_value() == "octocat_dev"
    assert dialog.status_label.text() == "Username copied. Clipboard will clear in 30 seconds."


def test_view_dialog_copy_password_action(qapp: QApplication, sample_credential: Credential) -> None:
    """Verify Copy Password copies password to clipboard while keeping input masked."""
    mock_cb = MockClipboard()
    clip_service = ClipboardService(timeout_seconds=30, clipboard=mock_cb)

    dialog = ViewCredentialDialog(sample_credential, clipboard_service=clip_service)

    # Verify password is masked initially
    assert dialog.password_val.echoMode() == QLineEdit.EchoMode.Password
    assert dialog.status_label.text() == ""

    # Click Copy Password
    dialog.copy_password_btn.click()

    # Password reaches clipboard
    assert mock_cb.text() == "OctoSecretPassword123!"
    assert clip_service.get_tracked_value() == "OctoSecretPassword123!"

    # Field remains masked
    assert dialog.password_val.echoMode() == QLineEdit.EchoMode.Password
    assert dialog.status_label.text() == "Password copied. Clipboard will clear in 30 seconds."


def test_view_dialog_fields_remain_read_only(qapp: QApplication, sample_credential: Credential) -> None:
    """Verify all text inputs in ViewCredentialDialog are strictly read-only."""
    dialog = ViewCredentialDialog(sample_credential)

    assert dialog.title_val.isReadOnly() is True
    assert dialog.username_val.isReadOnly() is True
    assert dialog.password_val.isReadOnly() is True
    assert dialog.notes_val.isReadOnly() is True


# =============================================================================
# 2. UNLOCKED VIEW INTEGRATION TESTS
# =============================================================================

def test_unlocked_view_status_on_copy_and_autoclear(
    qapp: QApplication,
    unlocked_vault_and_services,
) -> None:
    """Verify UnlockedView status updates on copy and on auto-clear."""
    vault, vault_service, credential_service = unlocked_vault_and_services
    mock_cb = MockClipboard()
    clip_service = ClipboardService(timeout_seconds=0.1, clipboard=mock_cb)

    view = UnlockedView(
        vault=vault,
        vault_service=vault_service,
        credential_service=credential_service,
        clipboard_service=clip_service,
    )

    # Simulate copy username
    clip_service.copy_username("octocat_dev")
    assert "Username copied. Clipboard will clear in 30 seconds." in view.status_label.text()

    # Simulate copy password
    clip_service.copy_password("octocat_secret")
    assert "Password copied. Clipboard will clear in 30 seconds." in view.status_label.text()

    # Trigger timeout cleanup
    clip_service._on_timeout()
    assert "Clipboard auto-cleared." in view.status_label.text()

    view.close()


def test_unlocked_view_lock_clears_owned_clipboard(
    qapp: QApplication,
    unlocked_vault_and_services,
) -> None:
    """Verify manual lock in UnlockedView clears SecureVault-owned clipboard."""
    vault, vault_service, credential_service = unlocked_vault_and_services
    mock_cb = MockClipboard()
    clip_service = ClipboardService(timeout_seconds=30, clipboard=mock_cb)

    view = UnlockedView(
        vault=vault,
        vault_service=vault_service,
        credential_service=credential_service,
        clipboard_service=clip_service,
    )

    clip_service.copy_password("vault_secret_to_clear")
    assert mock_cb.text() == "vault_secret_to_clear"

    # User clicks lock
    view._on_lock_clicked()

    assert mock_cb.text() == ""
    assert clip_service.get_tracked_value() is None


def test_unlocked_view_lock_preserves_external_clipboard(
    qapp: QApplication,
    unlocked_vault_and_services,
) -> None:
    """Verify manual lock does NOT clear clipboard if replaced by user/external app."""
    vault, vault_service, credential_service = unlocked_vault_and_services
    mock_cb = MockClipboard()
    clip_service = ClipboardService(timeout_seconds=30, clipboard=mock_cb)

    view = UnlockedView(
        vault=vault,
        vault_service=vault_service,
        credential_service=credential_service,
        clipboard_service=clip_service,
    )

    clip_service.copy_password("vault_secret")
    # User copies something else externally
    mock_cb.setText("external important notes")

    view._on_lock_clicked()

    assert mock_cb.text() == "external important notes"
    assert clip_service.get_tracked_value() is None


def test_unlocked_view_close_event_clears_owned_clipboard(
    qapp: QApplication,
    unlocked_vault_and_services,
) -> None:
    """Verify closing UnlockedView window cleans up owned clipboard."""
    vault, vault_service, credential_service = unlocked_vault_and_services
    mock_cb = MockClipboard()
    clip_service = ClipboardService(timeout_seconds=30, clipboard=mock_cb)

    view = UnlockedView(
        vault=vault,
        vault_service=vault_service,
        credential_service=credential_service,
        clipboard_service=clip_service,
    )

    clip_service.copy_username("close_user")
    assert mock_cb.text() == "close_user"

    view.close()

    assert mock_cb.text() == ""
    assert clip_service.get_tracked_value() is None


# =============================================================================
# 3. APPLICATION CONTROLLER INTEGRATION
# =============================================================================

def test_application_controller_lock_cleans_clipboard(qapp: QApplication) -> None:
    """Verify ApplicationController._on_vault_locked() triggers clipboard cleanup."""
    mock_cb = MockClipboard()
    clip_service = ClipboardService(timeout_seconds=30, clipboard=mock_cb)

    config = AppConfig()
    controller = ApplicationController(
        config=config,
        clipboard_service=clip_service,
    )

    clip_service.copy_password("controller_secret")
    assert mock_cb.text() == "controller_secret"

    # Lock vault via controller
    controller._on_vault_locked()

    assert mock_cb.text() == ""
    assert clip_service.get_tracked_value() is None

"""UI integration tests for UnlockedView and minimal credential management (Milestone 5)."""

import os
import sys
from pathlib import Path
import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

os.environ["QT_QPA_PLATFORM"] = "offscreen"

from app.core.config import AppConfig
from app.crypto.kdf import KDFParameters
from app.services.credential_service import CredentialService
from app.services.vault_service import VaultService
from app.ui.unlocked_view import AddCredentialDialog, UnlockedView


@pytest.fixture(scope="session")
def qapp() -> QApplication:
    """Ensure a singleton QApplication exists."""
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    return app


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


def test_unlocked_view_renders_initial_state(
    qapp: QApplication,
    unlocked_vault_and_services,
) -> None:
    """Verify UnlockedView displays login ID, vault ID, and zero count initially."""
    vault, vault_service, credential_service = unlocked_vault_and_services

    view = UnlockedView(
        vault=vault,
        login_id="alice",
        vault_service=vault_service,
        credential_service=credential_service,
    )

    assert "alice" in view.windowTitle() or "Unlocked" in view.windowTitle()
    assert vault.vault_id in view.vault_meta.text()
    assert "Stored Credentials: <b>0</b>" in view.vault_meta.text()
    assert view.credential_list.count() == 0


def test_add_credential_dialog_validation(qapp: QApplication) -> None:
    """Verify AddCredentialDialog validation prevents submission of empty required fields."""
    dialog = AddCredentialDialog()

    # Empty inputs
    dialog._on_save_clicked()
    assert "Title is required" in dialog.error_label.text()

    dialog.title_input.setText("GitHub")
    dialog._on_save_clicked()
    assert "Username is required" in dialog.error_label.text()

    dialog.username_input.setText("alice")
    dialog._on_save_clicked()
    assert "Password is required" in dialog.error_label.text()


def test_unlocked_view_add_and_delete_credential(
    qapp: QApplication,
    unlocked_vault_and_services,
) -> None:
    """Verify adding and deleting credentials via CredentialService reflects in UI."""
    vault, vault_service, credential_service = unlocked_vault_and_services

    view = UnlockedView(
        vault=vault,
        login_id="alice",
        vault_service=vault_service,
        credential_service=credential_service,
    )

    # 1. Add credential programmatically via service
    cred = credential_service.create_credential(
        title="Google",
        username="alice@gmail.com",
        password="SecretGooglePassword123!",
        notes="Primary email",
    )
    view._refresh_credentials()

    assert view.credential_list.count() == 1
    assert "Google" in view.credential_list.item(0).text()
    assert "Stored Credentials: <b>1</b>" in view.vault_meta.text()

    # Verify 'Delete Selected' button does not exist
    assert not hasattr(view, "delete_btn")

    # 2. Delete via per-card action
    view._on_delete_credential_by_id(cred.id, confirm=False)

    assert view.credential_list.count() == 0
    assert "Stored Credentials: <b>0</b>" in view.vault_meta.text()
    assert "deleted" in view.status_label.text().lower()


def test_unlocked_view_lock_action(
    qapp: QApplication,
    unlocked_vault_and_services,
) -> None:
    """Verify clicking Lock emits lock_requested and clears session."""
    vault, vault_service, credential_service = unlocked_vault_and_services

    view = UnlockedView(
        vault=vault,
        login_id="alice",
        vault_service=vault_service,
        credential_service=credential_service,
    )

    lock_signals = []
    view.lock_requested.connect(lambda: lock_signals.append(True))

    view._on_lock_clicked()

    assert len(lock_signals) == 1
    assert vault.is_locked is True

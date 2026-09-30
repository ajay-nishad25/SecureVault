"""Automated tests for Credential View & Edit UI (Milestone 5 Enhancement).

Verifies:
  - ViewCredentialDialog display, read-only behavior, and password masking (Show/Hide).
  - Absence of any "type" field.
  - EditCredentialDialog form population, field validation, and cancel behavior.
  - Critical test: Unchanged password in Edit mode is never overwritten by masked stars.
  - End-to-end persistence through Edit -> Lock -> Unlock -> Verify.
  - Multiple credential independence (View A, Edit B, Verify C unchanged, Delete B).
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QAbstractItemView, QApplication, QDialog, QLineEdit

os.environ["QT_QPA_PLATFORM"] = "offscreen"

from app.core.config import AppConfig
from app.crypto.kdf import KDFParameters
from app.models.credential import Credential
from app.services.credential_service import CredentialService
from app.services.vault_service import VaultService
from app.ui.unlocked_view import (
    CredentialCardWidget,
    EditCredentialDialog,
    UnlockedView,
    ViewCredentialDialog,
)


@pytest.fixture(scope="session")
def qapp() -> QApplication:
    """Ensure a singleton QApplication exists for GUI tests."""
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    return app


@pytest.fixture
def unlocked_setup(tmp_path: Path):
    """Provide an unlocked vault and initialized services in a temporary directory."""
    config = AppConfig(data_dir=tmp_path)
    vault_service = VaultService(config)
    vault = vault_service.create_vault(
        master_password="MasterTestPassword123!",
        kdf_params=KDFParameters.fast_for_testing(),
    )
    credential_service = CredentialService(vault_service)
    return vault, vault_service, credential_service, config


# ==============================================================================
# FEATURE 1: VIEW CREDENTIAL TESTS
# ==============================================================================

def test_view_credential_dialog_display_and_masking(qapp: QApplication) -> None:
    """Verify ViewCredentialDialog displays fields correctly with default password masking."""
    cred = Credential(
        title="ProtonMail",
        username="user@proton.me",
        password="VerySecretPassword123!",
        notes="Primary email account",
    )
    dialog = ViewCredentialDialog(cred)

    # 1. Title, username, notes are correct
    assert dialog.title_val.text() == "ProtonMail"
    assert dialog.username_val.text() == "user@proton.me"
    assert dialog.notes_val.text() == "Primary email account"

    # 2. All display fields are strictly read-only
    assert dialog.title_val.isReadOnly() is True
    assert dialog.username_val.isReadOnly() is True
    assert dialog.password_val.isReadOnly() is True
    assert dialog.notes_val.isReadOnly() is True

    # 3. Password is masked initially
    assert dialog.password_val.echoMode() == QLineEdit.EchoMode.Password
    assert dialog.toggle_pwd_btn.text() == "Show"

    # 4. Reveal password
    dialog.toggle_pwd_btn.click()
    assert dialog.password_val.echoMode() == QLineEdit.EchoMode.Normal
    assert dialog.toggle_pwd_btn.text() == "Hide"
    assert dialog.password_val.text() == "VerySecretPassword123!"

    # 5. Hide password again
    dialog.toggle_pwd_btn.click()
    assert dialog.password_val.echoMode() == QLineEdit.EchoMode.Password
    assert dialog.toggle_pwd_btn.text() == "Show"

    # 6. Verify strictly NO "type" field exists
    assert not hasattr(dialog, "type_input")
    assert not hasattr(dialog, "type_val")
    assert not hasattr(dialog, "category_input")

    # 7. Closing View leaves credential unchanged
    dialog.close_btn.click()
    assert cred.title == "ProtonMail"
    assert cred.password == "VerySecretPassword123!"


# ==============================================================================
# FEATURE 2: EDIT CREDENTIAL TESTS
# ==============================================================================

def test_edit_credential_dialog_population_and_masking(
    qapp: QApplication,
    unlocked_setup,
) -> None:
    """Verify EditCredentialDialog loads existing values and masks password."""
    _, _, credential_service, _ = unlocked_setup
    cred = credential_service.create_credential(
        title="GitHub",
        username="developer@github.com",
        password="GitHubSecretPassword789!",
        notes="Personal dev keys",
    )

    dialog = EditCredentialDialog(cred, credential_service)

    # 1. Existing values populated
    assert dialog.title_input.text() == "GitHub"
    assert dialog.username_input.text() == "developer@github.com"
    assert dialog.password_input.text() == "GitHubSecretPassword789!"
    assert dialog.notes_input.text() == "Personal dev keys"

    # 2. Password masked initially
    assert dialog.password_input.echoMode() == QLineEdit.EchoMode.Password
    assert dialog.toggle_pwd_btn.text() == "Show"

    # 3. Reveal and hide password
    dialog.toggle_pwd_btn.click()
    assert dialog.password_input.echoMode() == QLineEdit.EchoMode.Normal
    assert dialog.toggle_pwd_btn.text() == "Hide"

    dialog.toggle_pwd_btn.click()
    assert dialog.password_input.echoMode() == QLineEdit.EchoMode.Password
    assert dialog.toggle_pwd_btn.text() == "Show"

    # 4. Strictly NO "type" field exists
    assert not hasattr(dialog, "type_input")
    assert not hasattr(dialog, "category_input")


def test_edit_credential_dialog_validation(
    qapp: QApplication,
    unlocked_setup,
) -> None:
    """Verify EditCredentialDialog rejects empty required fields and stays open."""
    _, _, credential_service, _ = unlocked_setup
    cred = credential_service.create_credential(
        title="TestItem",
        username="testuser",
        password="testpassword",
    )

    dialog = EditCredentialDialog(cred, credential_service)

    # Empty title
    dialog.title_input.setText("")
    dialog._on_save_clicked()
    assert "Title is required" in dialog.error_label.text()
    assert dialog.result() != QDialog.DialogCode.Accepted

    # Restore title, empty username
    dialog.title_input.setText("Valid Title")
    dialog.username_input.setText("")
    dialog._on_save_clicked()
    assert "Username is required" in dialog.error_label.text()
    assert dialog.result() != QDialog.DialogCode.Accepted

    # Restore username, empty password
    dialog.username_input.setText("Valid User")
    dialog.password_input.setText("")
    dialog._on_save_clicked()
    assert "Password is required" in dialog.error_label.text()
    assert dialog.result() != QDialog.DialogCode.Accepted


def test_edit_credential_dialog_cancel_leaves_unchanged(
    qapp: QApplication,
    unlocked_setup,
) -> None:
    """Verify clicking Cancel on Edit dialog leaves original credential untouched."""
    _, _, credential_service, _ = unlocked_setup
    cred = credential_service.create_credential(
        title="UntouchedService",
        username="original_user",
        password="OriginalPassword999!",
        notes="Original notes",
    )

    dialog = EditCredentialDialog(cred, credential_service)
    dialog.title_input.setText("ChangedTitle")
    dialog.username_input.setText("changed_user")
    dialog.password_input.setText("ChangedPassword!")
    dialog.notes_input.setText("Changed notes")

    # Cancel
    dialog.cancel_btn.click()

    # Re-fetch from service
    fetched = credential_service.get_credential_or_raise(cred.id)
    assert fetched.title == "UntouchedService"
    assert fetched.username == "original_user"
    assert fetched.password == "OriginalPassword999!"
    assert fetched.notes == "Original notes"


def test_edit_credential_preserves_password_when_untouched(
    qapp: QApplication,
    unlocked_setup,
) -> None:
    """CRITICAL TEST: Editing only title/username must NEVER overwrite untouched password with masked stars."""
    _, _, credential_service, _ = unlocked_setup
    original_password = "OriginalPassword123"

    cred = credential_service.create_credential(
        title="OriginalTitle",
        username="user@example.com",
        password=original_password,
        notes="Untouched notes",
    )

    dialog = EditCredentialDialog(cred, credential_service)

    # Change only title
    dialog.title_input.setText("UpdatedTitle")
    # Do NOT touch password field
    dialog._on_save_clicked()

    # Verify updated in service
    updated = credential_service.get_credential_or_raise(cred.id)
    assert updated.title == "UpdatedTitle"
    assert updated.password == original_password
    assert updated.password != "********"
    assert updated.id == cred.id


def test_edit_credential_updates_all_fields_and_preserves_id(
    qapp: QApplication,
    unlocked_setup,
) -> None:
    """Verify editing all fields updates credential while keeping the exact same ID and item count."""
    _, _, credential_service, _ = unlocked_setup
    cred = credential_service.create_credential(
        title="InitialTitle",
        username="initial_user",
        password="initial_password",
        notes="initial_notes",
    )
    original_id = cred.id

    dialog = EditCredentialDialog(cred, credential_service)
    dialog.title_input.setText("NewTitle")
    dialog.username_input.setText("new_user")
    dialog.password_input.setText("NewPassword999!")
    dialog.notes_input.setText("new_notes")
    dialog._on_save_clicked()

    updated = credential_service.get_credential_or_raise(original_id)
    assert updated.id == original_id
    assert updated.title == "NewTitle"
    assert updated.username == "new_user"
    assert updated.password == "NewPassword999!"
    assert updated.notes == "new_notes"

    # Confirm no duplicate
    all_creds = credential_service.get_all_credentials()
    assert len(all_creds) == 1


# ==============================================================================
# FEATURE 3: PERSISTENCE & RELOAD TEST
# ==============================================================================

def test_edit_credential_persistence_across_lock_and_unlock(
    qapp: QApplication,
    unlocked_setup,
) -> None:
    """Verify: Create -> Edit -> Save -> Lock -> Unlock -> Read preserves all updated fields."""
    vault, vault_service, credential_service, config = unlocked_setup

    # 1. Create credential
    cred = credential_service.create_credential(
        title="BeforeEdit",
        username="user_v1",
        password="PasswordV1!",
        notes="Notes V1",
    )
    cred_id = cred.id

    # 2. Edit credential via service / dialog
    dialog = EditCredentialDialog(cred, credential_service)
    dialog.title_input.setText("AfterEdit")
    dialog.username_input.setText("user_v2")
    dialog.password_input.setText("PasswordV2!")
    dialog.notes_input.setText("Notes V2")
    dialog._on_save_clicked()

    # 3. Lock vault
    vault_service.lock_vault()
    assert vault_service.active_vault is None

    # 4. Re-unlock vault
    reloaded_vault = vault_service.unlock_vault("MasterTestPassword123!")
    assert reloaded_vault.is_locked is False

    # 5. Read credential and verify all updated fields
    reloaded_service = CredentialService(vault_service)
    reloaded_cred = reloaded_service.get_credential_or_raise(cred_id)
    assert reloaded_cred.id == cred_id
    assert reloaded_cred.title == "AfterEdit"
    assert reloaded_cred.username == "user_v2"
    assert reloaded_cred.password == "PasswordV2!"
    assert reloaded_cred.notes == "Notes V2"


# ==============================================================================
# FEATURE 4: MULTIPLE CREDENTIALS INDEPENDENCE TEST
# ==============================================================================

def test_multiple_credentials_view_edit_delete_independence(
    qapp: QApplication,
    unlocked_setup,
) -> None:
    """Verify independent operations across multiple credentials:
    Create GitHub, Google, LinkedIn.
    - View GitHub -> shows GitHub
    - Edit Google -> only Google changes
    - View LinkedIn -> remains unchanged
    - Delete Google -> only Google disappears
    """
    vault, vault_service, credential_service, _ = unlocked_setup

    # 1. Create 3 distinct credentials
    c_github = credential_service.create_credential(
        title="GitHub",
        username="dev@github.com",
        password="GithubPassword123!",
        notes="GitHub work",
    )
    c_google = credential_service.create_credential(
        title="Google",
        username="user@gmail.com",
        password="GooglePassword456!",
        notes="Personal email",
    )
    c_linkedin = credential_service.create_credential(
        title="LinkedIn",
        username="pro@linkedin.com",
        password="LinkedinPassword789!",
        notes="Professional network",
    )

    view = UnlockedView(
        vault=vault,
        login_id="alice",
        vault_service=vault_service,
        credential_service=credential_service,
    )

    assert view.credential_list.count() == 3

    # 2. View GitHub -> shows GitHub details
    github_dialog = ViewCredentialDialog(c_github)
    assert github_dialog.title_val.text() == "GitHub"
    assert github_dialog.username_val.text() == "dev@github.com"
    assert github_dialog.password_val.text() == "GithubPassword123!"

    # 3. Edit Google -> only Google changes
    google_dialog = EditCredentialDialog(c_google, credential_service)
    google_dialog.title_input.setText("Google Workspace")
    google_dialog.password_input.setText("NewGooglePassword999!")
    google_dialog._on_save_clicked()

    # Verify Google updated
    updated_google = credential_service.get_credential_or_raise(c_google.id)
    assert updated_google.title == "Google Workspace"
    assert updated_google.password == "NewGooglePassword999!"

    # Verify LinkedIn is strictly unchanged
    linkedin = credential_service.get_credential_or_raise(c_linkedin.id)
    assert linkedin.title == "LinkedIn"
    assert linkedin.username == "pro@linkedin.com"
    assert linkedin.password == "LinkedinPassword789!"
    assert linkedin.notes == "Professional network"

    # Verify GitHub is strictly unchanged
    github = credential_service.get_credential_or_raise(c_github.id)
    assert github.title == "GitHub"
    assert github.username == "dev@github.com"
    assert github.password == "GithubPassword123!"

    # 4. Delete Google -> only Google disappears
    view._on_delete_credential_by_id(c_google.id, confirm=False)

    remaining = credential_service.get_all_credentials()
    assert len(remaining) == 2
    remaining_titles = [c.title for c in remaining]
    assert "Google Workspace" not in remaining_titles
    assert "GitHub" in remaining_titles
    assert "LinkedIn" in remaining_titles
    assert view.credential_list.count() == 2


# ==============================================================================
# FEATURE 5: UI CARD WIDGET INTERACTIONS
# ==============================================================================

def test_credential_card_widget_signals(qapp: QApplication) -> None:
    """Verify CredentialCardWidget emits view, edit, and delete signals with cred_id."""
    card = CredentialCardWidget(
        cred_id="uuid-1234",
        title="TestCard",
        username="card_user",
        notes="card_notes",
    )

    view_emitted = []
    edit_emitted = []
    delete_emitted = []

    card.view_clicked.connect(lambda cid: view_emitted.append(cid))
    card.edit_clicked.connect(lambda cid: edit_emitted.append(cid))
    card.delete_clicked.connect(lambda cid: delete_emitted.append(cid))

    card.view_btn.click()
    card.edit_btn.click()
    card.delete_btn.click()

    assert view_emitted == ["uuid-1234"]
    assert edit_emitted == ["uuid-1234"]
    assert delete_emitted == ["uuid-1234"]


def test_credential_card_layout_geometry_and_notes_omission(qapp: QApplication) -> None:
    """Verify CredentialCardWidget has clean layout hierarchy and omits notes when empty."""
    # 1. Card WITH notes
    card_with_notes = CredentialCardWidget(
        cred_id="id-1",
        title="GitHub",
        username="ajay@example.com",
        notes="Personal GitHub account",
    )
    assert card_with_notes.title_label.text() == "GitHub"
    assert card_with_notes.username_label.text() == "ajay@example.com"
    assert card_with_notes.notes_label is not None
    assert card_with_notes.notes_label.text() == "Personal GitHub account"

    # Verify buttons are present
    assert card_with_notes.view_btn.text() == "👁 View"
    assert card_with_notes.edit_btn.text() == "✏️ Edit"
    assert card_with_notes.delete_btn.text() == "🗑 Delete"

    # Layout hierarchy: title is above username, username is above notes, buttons at bottom
    layout = card_with_notes.layout()
    assert layout.itemAt(0).widget() == card_with_notes.title_label
    assert layout.itemAt(1).widget() == card_with_notes.username_label
    assert layout.itemAt(2).widget() == card_with_notes.notes_label

    # 2. Card WITHOUT notes (empty string and whitespace)
    card_no_notes = CredentialCardWidget(
        cred_id="id-2",
        title="Google",
        username="user@gmail.com",
        notes="   ",
    )
    assert card_no_notes.title_label.text() == "Google"
    assert card_no_notes.username_label.text() == "user@gmail.com"
    assert card_no_notes.notes_label is None  # Strictly omitted!

    # Card with notes requires more height than card without notes
    assert card_with_notes.sizeHint().height() > card_no_notes.sizeHint().height()


def test_multiple_credential_cards_scaling_and_varied_lengths(
    qapp: QApplication,
    unlocked_setup,
) -> None:
    """Verify clean rendering across 1, 3, and 6 credentials with extreme text lengths."""
    vault, vault_service, credential_service, _ = unlocked_setup

    test_data = [
        # (title, username, notes)
        ("A", "b", ""),  # minimal length, empty notes
        ("GitHub", "developer@github.com", "Standard work account"),
        ("Corporate AWS Root Account", "admin-service-account@aws.internal", ""),
        (
            "Super Long Organization Name That Exceeds Normal Lengths For Testing Word Wrapping",
            "extended_service_account_developer_testing_identity@subdomain.corporate.domain.com",
            "This is a very long multiline note description providing backup tokens and rotation info.",
        ),
        ("LinkedIn", "user@linkedin.com", "Professional network"),
        ("Slack", "worker@workspace.slack.com", "Daily team communications"),
    ]

    # Create all credentials
    for title, username, notes in test_data:
        credential_service.create_credential(
            title=title,
            username=username,
            password="TestPassword123!",
            notes=notes,
        )

    view = UnlockedView(
        vault=vault,
        login_id="tester",
        vault_service=vault_service,
        credential_service=credential_service,
    )

    # 6 items rendered in QListWidget
    assert view.credential_list.count() == 6

    for row, (expected_title, expected_username, expected_notes) in enumerate(test_data):
        item = view.credential_list.item(row)
        assert item is not None
        card = view.credential_list.itemWidget(item)
        assert isinstance(card, CredentialCardWidget)

        # Title and username match exactly
        assert card.title_label.text() == expected_title
        assert card.username_label.text() == expected_username

        # Notes preview correctly populated or omitted
        if expected_notes.strip():
            assert card.notes_label is not None
            assert card.notes_label.text() == expected_notes.strip()
        else:
            assert card.notes_label is None

        # Verify buttons exist and are functional
        assert card.view_btn.isEnabled()
        assert card.edit_btn.isEnabled()
        assert card.delete_btn.isEnabled()

        # Item sizeHint accommodates the full card height without squashing
        assert item.sizeHint().height() >= 70


# ==============================================================================
# FEATURE 6: FINAL M5 UI POLISH TESTS (DELETE SELECTED REMOVED, CONFIRMATION, SCROLLING)
# ==============================================================================

def test_delete_selected_button_removed_and_per_card_remains(
    qapp: QApplication,
    unlocked_setup,
) -> None:
    """TEST 1: Verify 'Delete Selected' button was removed, selection deletion is gone, and per-card Delete remains."""
    vault, vault_service, credential_service, _ = unlocked_setup

    c = credential_service.create_credential("GitHub", "dev", "pwd", "notes")
    view = UnlockedView(
        vault=vault,
        login_id="alice",
        vault_service=vault_service,
        credential_service=credential_service,
    )

    # 1. 'Delete Selected' button must NOT exist on UnlockedView
    assert not hasattr(view, "delete_btn")
    assert not hasattr(view, "_on_delete_clicked")

    # 2. Only Add Credential, Lock Vault, and Exit buttons exist in bottom bar
    assert hasattr(view, "add_btn")
    assert hasattr(view, "lock_btn")
    assert hasattr(view, "exit_btn")

    # 3. Per-card Delete button exists on the credential card
    item = view.credential_list.item(0)
    card = view.credential_list.itemWidget(item)
    assert hasattr(card, "delete_btn")
    assert card.delete_btn.text() == "🗑 Delete"


def test_delete_confirmation_cancel_and_confirm_lifecycle(
    qapp: QApplication,
    unlocked_setup,
    monkeypatch,
) -> None:
    """TEST 2: Verify delete confirmation dialog lifecycle:
    Click card Delete -> Confirmation appears -> Cancel leaves credential -> Delete removes credential.
    """
    vault, vault_service, credential_service, _ = unlocked_setup
    cred = credential_service.create_credential("GitHub", "octo", "pass123", "notes")

    view = UnlockedView(
        vault=vault,
        login_id="alice",
        vault_service=vault_service,
        credential_service=credential_service,
    )
    assert view.credential_list.count() == 1
    assert "Stored Credentials: <b>1</b>" in view.vault_meta.text()

    # Step 1: User clicks Delete, but chooses CANCEL on confirmation
    monkeypatch.setattr(view, "_confirm_deletion", lambda title: False)
    view._on_delete_credential_by_id(cred.id)

    # Credential remains untouched
    assert view.credential_list.count() == 1
    assert credential_service.get_credential(cred.id) is not None
    assert "Stored Credentials: <b>1</b>" in view.vault_meta.text()

    # Step 2: User clicks Delete, and confirms DELETION
    monkeypatch.setattr(view, "_confirm_deletion", lambda title: True)
    view._on_delete_credential_by_id(cred.id)

    # Credential removed and counter updated
    assert view.credential_list.count() == 0
    assert credential_service.get_credential(cred.id) is None
    assert "Stored Credentials: <b>0</b>" in view.vault_meta.text()


def test_delete_confirmation_correct_credential_identified(
    qapp: QApplication,
    unlocked_setup,
    monkeypatch,
) -> None:
    """TEST 3: Verify confirmation identifies the specific credential by title,
    and cancelling/confirming only affects the targeted credential.
    """
    vault, vault_service, credential_service, _ = unlocked_setup

    c_github = credential_service.create_credential("GitHub", "dev1", "p1", "")
    c_google = credential_service.create_credential("Google", "dev2", "p2", "")
    c_linkedin = credential_service.create_credential("LinkedIn", "dev3", "p3", "")

    view = UnlockedView(
        vault=vault,
        login_id="alice",
        vault_service=vault_service,
        credential_service=credential_service,
    )
    assert view.credential_list.count() == 3

    identified_titles = []

    def mock_confirm_cancel(title: str) -> bool:
        identified_titles.append(title)
        return False

    def mock_confirm_delete(title: str) -> bool:
        identified_titles.append(title)
        return True

    # 1. Target Google, user cancels
    monkeypatch.setattr(view, "_confirm_deletion", mock_confirm_cancel)
    view._on_delete_credential_by_id(c_google.id)

    assert identified_titles == ["Google"]  # Correct credential identified!
    assert view.credential_list.count() == 3
    assert len(credential_service.get_all_credentials()) == 3

    # 2. Target Google again, user confirms delete
    monkeypatch.setattr(view, "_confirm_deletion", mock_confirm_delete)
    view._on_delete_credential_by_id(c_google.id)

    assert identified_titles == ["Google", "Google"]
    assert view.credential_list.count() == 2
    remaining = [c.title for c in credential_service.get_all_credentials()]
    assert "Google" not in remaining
    assert "GitHub" in remaining
    assert "LinkedIn" in remaining


def test_credential_persistence_after_delete_with_confirmation(
    qapp: QApplication,
    unlocked_setup,
    monkeypatch,
) -> None:
    """TEST 4: Verify deleted credential remains deleted after Lock -> Unlock persistence cycle."""
    vault, vault_service, credential_service, _ = unlocked_setup

    c_keep = credential_service.create_credential("PersistentItem", "user1", "p1", "")
    c_delete = credential_service.create_credential("ItemToDelete", "user2", "p2", "")

    view = UnlockedView(
        vault=vault,
        login_id="alice",
        vault_service=vault_service,
        credential_service=credential_service,
    )

    # Delete with confirmation
    monkeypatch.setattr(view, "_confirm_deletion", lambda title: True)
    view._on_delete_credential_by_id(c_delete.id)

    # Lock vault session
    view._on_lock_clicked()
    assert vault_service.active_vault is None

    # Re-unlock vault
    reloaded_vault = vault_service.unlock_vault("MasterTestPassword123!")
    reloaded_service = CredentialService(vault_service)

    assert reloaded_vault.item_count == 1
    assert reloaded_service.get_credential(c_delete.id) is None
    assert reloaded_service.get_credential(c_keep.id) is not None
    assert reloaded_service.get_credential(c_keep.id).title == "PersistentItem"


def test_credential_list_smooth_pixel_scrolling_configuration(
    qapp: QApplication,
    unlocked_setup,
) -> None:
    """TEST 5: Verify the credential list uses pixel-based smooth scrolling,
    with a configured single step and stable cards across 10+ entries.
    """
    vault, vault_service, credential_service, _ = unlocked_setup

    view = UnlockedView(
        vault=vault,
        login_id="alice",
        vault_service=vault_service,
        credential_service=credential_service,
    )

    # Verify ScrollPerPixel is configured
    assert (
        view.credential_list.verticalScrollMode()
        == QAbstractItemView.ScrollMode.ScrollPerPixel
    )
    assert (
        view.credential_list.horizontalScrollMode()
        == QAbstractItemView.ScrollMode.ScrollPerPixel
    )

    # Verify smooth scrollbar single step
    assert view.credential_list.verticalScrollBar().singleStep() > 0
    assert view.credential_list.verticalScrollBar().singleStep() <= 20

    # Populate 12 credentials to test scrolling stability with large list
    for i in range(12):
        notes = f"Notes for account {i}" if i % 2 == 0 else ""
        credential_service.create_credential(
            title=f"Service {i:02d}",
            username=f"user_{i}@example.com",
            password=f"SecretPass{i}!",
            notes=notes,
        )

    view._refresh_credentials()
    assert view.credential_list.count() == 12

    # Verify cards remain intact with functional buttons and valid layout
    for i in range(12):
        item = view.credential_list.item(i)
        card = view.credential_list.itemWidget(item)
        assert isinstance(card, CredentialCardWidget)
        assert card.view_btn.isEnabled()
        assert card.edit_btn.isEnabled()
        assert card.delete_btn.isEnabled()
        assert item.sizeHint().height() >= 70


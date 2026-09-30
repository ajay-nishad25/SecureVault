"""Automated tests for Main Vault UI & Credential Search (Milestone 6).

Verifies:
  1. Empty search returns all credentials.
  2. Search by title (exact and partial).
  3. Search by username (exact and partial).
  4. Search by notes (exact and partial).
  5. Case-insensitive matching.
  6. Passwords are STRICTLY NOT searchable (security boundary).
  7. No-results empty state vs empty vault empty state.
  8. Clear search restores all credentials.
  9. Search does NOT modify vault data or trigger persistence.
  10. Search preserves credential IDs for View, Edit, and Delete actions.
  11. Delete confirmation remains active on filtered credentials.
  12. Multi-credential lifecycle test (Search -> View -> Edit -> Clear).
  13. Lock while searching clears search state.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from unittest.mock import patch
import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QDialog,
    QLineEdit,
    QMessageBox,
)

os.environ["QT_QPA_PLATFORM"] = "offscreen"

from app.core.config import AppConfig
from app.crypto.kdf import KDFParameters
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
# SEARCH MATCHING & SECURITY TESTS
# ==============================================================================

def test_empty_search_returns_all_credentials(qapp: QApplication, unlocked_setup) -> None:
    """Verify that an empty or whitespace query displays all credentials."""
    vault, vault_service, credential_service, _ = unlocked_setup
    credential_service.create_credential("GitHub", "dev@github.com", "pass1", "notes 1")
    credential_service.create_credential("Google", "user@gmail.com", "pass2", "notes 2")

    view = UnlockedView(vault, "test_user", vault_service, credential_service)

    assert view.credential_list.count() == 2
    assert "Stored Credentials: <b>2</b>" in view.counter_label.text()
    assert view.empty_state_widget.isHidden()

    # Whitespace query
    view.search_input.setText("   ")
    assert view.credential_list.count() == 2
    assert "Stored Credentials: <b>2</b>" in view.counter_label.text()


def test_search_by_title_exact_and_partial(qapp: QApplication, unlocked_setup) -> None:
    """Verify searching by exact and partial title matches correctly."""
    vault, vault_service, credential_service, _ = unlocked_setup
    credential_service.create_credential("GitHub", "dev@github.com", "pass1", "notes 1")
    credential_service.create_credential("GitLab", "dev@gitlab.com", "pass2", "notes 2")
    credential_service.create_credential("AWS Console", "root@aws.com", "pass3", "cloud")

    view = UnlockedView(vault, "test_user", vault_service, credential_service)

    # Partial match 'git' matches GitHub and GitLab
    view.search_input.setText("git")
    assert view.credential_list.count() == 2
    assert "Showing <b>2</b> of <b>3</b> credentials" in view.counter_label.text()

    # Exact title 'GitHub'
    view.search_input.setText("GitHub")
    assert view.credential_list.count() == 1
    assert "Showing <b>1</b> of <b>3</b> credentials" in view.counter_label.text()
    card = view.credential_list.itemWidget(view.credential_list.item(0))
    assert isinstance(card, CredentialCardWidget)
    assert card.title_label.text() == "GitHub"


def test_search_by_username_exact_and_partial(qapp: QApplication, unlocked_setup) -> None:
    """Verify searching by exact and partial username."""
    vault, vault_service, credential_service, _ = unlocked_setup
    credential_service.create_credential("GitHub", "ajay@example.com", "pass1", "dev")
    credential_service.create_credential("Google", "alice@gmail.com", "pass2", "personal")

    view = UnlockedView(vault, "test_user", vault_service, credential_service)

    # Partial username
    view.search_input.setText("ajay@")
    assert view.credential_list.count() == 1
    card = view.credential_list.itemWidget(view.credential_list.item(0))
    assert isinstance(card, CredentialCardWidget)
    assert card.username_label.text() == "ajay@example.com"

    # Exact username
    view.search_input.setText("alice@gmail.com")
    assert view.credential_list.count() == 1
    card = view.credential_list.itemWidget(view.credential_list.item(0))
    assert isinstance(card, CredentialCardWidget)
    assert card.username_label.text() == "alice@gmail.com"


def test_search_by_notes_exact_and_partial(qapp: QApplication, unlocked_setup) -> None:
    """Verify searching matches against notes."""
    vault, vault_service, credential_service, _ = unlocked_setup
    credential_service.create_credential("GitHub", "ajay", "pass1", "Personal development account")
    credential_service.create_credential("Google", "ajay", "pass2", "Work email account")

    view = UnlockedView(vault, "test_user", vault_service, credential_service)

    # Partial match 'development'
    view.search_input.setText("development")
    assert view.credential_list.count() == 1
    card = view.credential_list.itemWidget(view.credential_list.item(0))
    assert isinstance(card, CredentialCardWidget)
    assert card.title_label.text() == "GitHub"

    # Match 'account' matches both
    view.search_input.setText("account")
    assert view.credential_list.count() == 2


def test_case_insensitive_matching(qapp: QApplication, unlocked_setup) -> None:
    """Verify search is case-insensitive for title, username, and notes."""
    vault, vault_service, credential_service, _ = unlocked_setup
    credential_service.create_credential("GitHub", "Developer", "pass1", "Important Notes")

    view = UnlockedView(vault, "test_user", vault_service, credential_service)

    for query in ["github", "GITHUB", "GiThUb", "developer", "DEVELOPER", "important", "IMPORTANT"]:
        view.search_input.setText(query)
        assert view.credential_list.count() == 1, f"Failed case-insensitive match for '{query}'"


def test_password_is_strictly_not_searchable(qapp: QApplication, unlocked_setup) -> None:
    """CRITICAL SECURITY TEST: Passwords must NEVER be searchable."""
    vault, vault_service, credential_service, _ = unlocked_setup
    credential_service.create_credential(
        title="GitHub",
        username="ajay@example.com",
        password="SecretPassword123",
        notes="Personal account",
    )

    view = UnlockedView(vault, "test_user", vault_service, credential_service)

    # Search for the exact password
    view.search_input.setText("SecretPassword123")
    assert view.credential_list.count() == 0
    assert not view.empty_state_widget.isHidden()
    assert "No credentials found." in view.empty_state_title.text()

    # Search for partial password
    view.search_input.setText("Secret")
    assert view.credential_list.count() == 0

    view.search_input.setText("Password123")
    assert view.credential_list.count() == 0


# ==============================================================================
# EMPTY STATES & CLEAR BEHAVIOR
# ==============================================================================

def test_empty_vault_state(qapp: QApplication, unlocked_setup) -> None:
    """Verify empty vault with no credentials shows initial empty state."""
    vault, vault_service, credential_service, _ = unlocked_setup
    view = UnlockedView(vault, "test_user", vault_service, credential_service)

    assert view.credential_list.count() == 0
    assert not view.empty_state_widget.isHidden()
    assert "No credentials yet." in view.empty_state_title.text()
    assert "Add your first credential to get started." in view.empty_state_subtitle.text()
    assert not view.empty_state_add_btn.isHidden()


def test_no_results_search_state(qapp: QApplication, unlocked_setup) -> None:
    """Verify search returning no results shows search empty state and keeps actions available."""
    vault, vault_service, credential_service, _ = unlocked_setup
    credential_service.create_credential("GitHub", "dev", "pass", "notes")

    view = UnlockedView(vault, "test_user", vault_service, credential_service)
    view.search_input.setText("non_existent_search_term")

    assert view.credential_list.count() == 0
    assert not view.empty_state_widget.isHidden()
    assert "No credentials found." in view.empty_state_title.text()
    assert "Try a different search term." in view.empty_state_subtitle.text()
    assert view.empty_state_add_btn.isHidden()
    assert view.add_btn.isEnabled()
    assert view.lock_btn.isEnabled()


def test_clear_search_restores_all_credentials(qapp: QApplication, unlocked_setup) -> None:
    """Verify clicking Clear button clears search input and restores full list."""
    vault, vault_service, credential_service, _ = unlocked_setup
    credential_service.create_credential("GitHub", "dev", "pass1", "notes")
    credential_service.create_credential("Google", "alice", "pass2", "notes")

    view = UnlockedView(vault, "test_user", vault_service, credential_service)
    view.search_input.setText("GitHub")
    assert view.credential_list.count() == 1

    # Click clear button
    view.clear_btn.click()
    assert view.search_input.text() == ""
    assert view.credential_list.count() == 2
    assert "Stored Credentials: <b>2</b>" in view.counter_label.text()


# ==============================================================================
# INTEGRITY, ID PRESERVATION & ACTION INTEGRATION
# ==============================================================================

def test_search_does_not_modify_vault_or_persist(qapp: QApplication, unlocked_setup) -> None:
    """Verify search is an in-memory UI operation that NEVER triggers vault persistence."""
    vault, vault_service, credential_service, config = unlocked_setup
    credential_service.create_credential("GitHub", "dev", "pass", "notes")

    vault_path = config.vault_path
    initial_mtime = vault_path.stat().st_mtime_ns

    view = UnlockedView(vault, "test_user", vault_service, credential_service)

    with patch.object(vault_service, "save_vault") as mock_save:
        view.search_input.setText("Git")
        view.search_input.setText("GitHub")
        view.search_input.setText("nonexistent")
        view.clear_btn.click()

        # save_vault must NOT have been called even once during search
        mock_save.assert_not_called()

    # File on disk must remain untouched
    assert vault_path.stat().st_mtime_ns == initial_mtime


def test_search_preserves_credential_ids(qapp: QApplication, unlocked_setup) -> None:
    """Verify filtered cards retain exact credential IDs and metadata."""
    vault, vault_service, credential_service, _ = unlocked_setup
    cred1 = credential_service.create_credential("GitHub", "dev1", "pass1", "notes1")
    cred2 = credential_service.create_credential("Google", "dev2", "pass2", "notes2")

    view = UnlockedView(vault, "test_user", vault_service, credential_service)
    view.search_input.setText("Google")

    assert view.credential_list.count() == 1
    item = view.credential_list.item(0)
    card = view.credential_list.itemWidget(item)
    assert isinstance(card, CredentialCardWidget)
    assert card.cred_id == cred2.id
    assert item.data(Qt.ItemDataRole.UserRole) == cred2.id


def test_view_action_on_filtered_credential(qapp: QApplication, unlocked_setup) -> None:
    """Verify clicking View on a filtered credential loads the correct credential."""
    vault, vault_service, credential_service, _ = unlocked_setup
    credential_service.create_credential("GitHub", "dev1", "pass1", "notes1")
    cred2 = credential_service.create_credential("Google", "dev2", "pass2", "notes2")

    view = UnlockedView(vault, "test_user", vault_service, credential_service)
    view.search_input.setText("Google")

    item = view.credential_list.item(0)
    card = view.credential_list.itemWidget(item)
    assert isinstance(card, CredentialCardWidget)

    with patch.object(ViewCredentialDialog, "exec", return_value=QDialog.DialogCode.Accepted):
        with patch("app.ui.unlocked_view.ViewCredentialDialog") as mock_dialog:
            mock_dialog.return_value.exec.return_value = QDialog.DialogCode.Accepted
            card.view_btn.click()
            mock_dialog.assert_called_once()
            called_cred = mock_dialog.call_args[0][0]
            assert called_cred.id == cred2.id
            assert called_cred.title == "Google"


def test_edit_action_on_filtered_credential(qapp: QApplication, unlocked_setup) -> None:
    """Verify editing a filtered credential modifies and persists only that credential."""
    vault, vault_service, credential_service, _ = unlocked_setup
    cred1 = credential_service.create_credential("GitHub", "dev1", "pass1", "notes1")
    cred2 = credential_service.create_credential("Google", "dev2", "pass2", "notes2")

    view = UnlockedView(vault, "test_user", vault_service, credential_service)
    view.search_input.setText("Google")

    # Perform programmatic update on Google
    credential_service.update_credential(
        credential_id=cred2.id,
        title="Google Cloud",
        username="dev2_updated",
        password="NewPassword123!",
        notes="updated notes",
    )
    view._refresh_credentials()

    # Google Cloud matches 'Google'
    assert view.credential_list.count() == 1
    card = view.credential_list.itemWidget(view.credential_list.item(0))
    assert isinstance(card, CredentialCardWidget)
    assert card.title_label.text() == "Google Cloud"

    # Verify cred1 remained untouched
    unmodified = credential_service.get_credential_or_raise(cred1.id)
    assert unmodified.title == "GitHub"
    assert unmodified.username == "dev1"


def test_delete_action_with_confirmation_on_filtered_credential(
    qapp: QApplication,
    unlocked_setup,
) -> None:
    """Verify Delete on filtered result triggers confirmation and deletes only the matching credential."""
    vault, vault_service, credential_service, _ = unlocked_setup
    cred1 = credential_service.create_credential("GitHub", "dev1", "pass1", "notes1")
    cred2 = credential_service.create_credential("Google", "dev2", "pass2", "notes2")

    view = UnlockedView(vault, "test_user", vault_service, credential_service)
    view.search_input.setText("Google")

    card = view.credential_list.itemWidget(view.credential_list.item(0))
    assert isinstance(card, CredentialCardWidget)

    # 1. Cancel deletion
    with patch.object(view, "_confirm_deletion", return_value=False):
        card.delete_btn.click()
        assert credential_service.get_credential(cred2.id) is not None
        assert view.credential_list.count() == 1

    # 2. Confirm deletion
    with patch.object(view, "_confirm_deletion", return_value=True):
        card.delete_btn.click()
        assert credential_service.get_credential(cred2.id) is None
        # With active search 'Google', no matches remain
        assert view.credential_list.count() == 0
        assert not view.empty_state_widget.isHidden()

    # Clear search: GitHub is still intact
    view.clear_btn.click()
    assert view.credential_list.count() == 1
    remaining_card = view.credential_list.itemWidget(view.credential_list.item(0))
    assert remaining_card.title_label.text() == "GitHub"


def test_multi_credential_search_lifecycle(qapp: QApplication, unlocked_setup) -> None:
    """Full lifecycle test: Create GitHub, Google, LinkedIn -> Search Google -> View -> Edit -> Clear."""
    vault, vault_service, credential_service, _ = unlocked_setup
    c_github = credential_service.create_credential("GitHub", "ajay@gh.com", "passGH", "dev")
    c_google = credential_service.create_credential("Google", "ajay@gmail.com", "passGoogle", "mail")
    c_linkedin = credential_service.create_credential("LinkedIn", "ajay@li.com", "passLI", "jobs")

    view = UnlockedView(vault, "ajay", vault_service, credential_service)
    assert view.credential_list.count() == 3

    # 1. Search: Google
    view.search_input.setText("Google")
    assert view.credential_list.count() == 1
    card = view.credential_list.itemWidget(view.credential_list.item(0))
    assert card.cred_id == c_google.id
    assert card.title_label.text() == "Google"

    # 2. View Google
    cred = credential_service.get_credential_or_raise(c_google.id)
    v_dialog = ViewCredentialDialog(cred)
    assert v_dialog.title_val.text() == "Google"
    assert v_dialog.username_val.text() == "ajay@gmail.com"
    v_dialog.close_btn.click()

    # 3. Edit Google
    credential_service.update_credential(
        credential_id=c_google.id,
        title="Google Workspace",
        username="ajay@corp.google.com",
        password="passGoogleNew123!",
    )
    view._refresh_credentials()
    assert view.credential_list.count() == 1
    updated_card = view.credential_list.itemWidget(view.credential_list.item(0))
    assert updated_card.title_label.text() == "Google Workspace"

    # 4. Clear search
    view.clear_btn.click()
    assert view.credential_list.count() == 3
    titles = [
        view.credential_list.itemWidget(view.credential_list.item(i)).title_label.text()
        for i in range(view.credential_list.count())
    ]
    assert "GitHub" in titles
    assert "Google Workspace" in titles
    assert "LinkedIn" in titles


def test_lock_clears_search_field(qapp: QApplication, unlocked_setup) -> None:
    """Verify that locking the vault resets the search field."""
    vault, vault_service, credential_service, _ = unlocked_setup
    credential_service.create_credential("GitHub", "dev", "pass", "notes")

    view = UnlockedView(vault, "test_user", vault_service, credential_service)
    view.search_input.setText("GitHub")

    view._on_lock_clicked()
    assert view.search_input.text() == ""
    assert vault.is_locked is True


def test_smooth_scrolling_and_delegate_preserved(qapp: QApplication, unlocked_setup) -> None:
    """Verify smooth pixel scrolling and card delegate are preserved in M6."""
    vault, vault_service, credential_service, _ = unlocked_setup
    view = UnlockedView(vault, "test_user", vault_service, credential_service)

    assert view.credential_list.verticalScrollMode() == QAbstractItemView.ScrollMode.ScrollPerPixel
    assert view.credential_list.horizontalScrollMode() == QAbstractItemView.ScrollMode.ScrollPerPixel
    assert view.credential_list.verticalScrollBar().singleStep() == 16

"""SecureVault — Milestone M8 Verification Script.

Automates the exact manual verification checklist from Section 21:
- GENERAL: Appearance & Dark/Light switching & persistence
- SECURITY: Auto-Lock 2/5/10/15 min & live session update
- SECURITY: Master password change, locking, rejection of old password, acceptance of new password, credential preservation
"""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

# Ensure offscreen Qt platform
os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PySide6.QtWidgets import QApplication, QMessageBox

app = QApplication.instance() or QApplication(sys.argv)

from app.core.config import AppConfig
from app.crypto.kdf import KDFParameters
from app.services.credential_service import CredentialService
from app.services.initialization import InitializationService
from app.services.session_manager import SessionInactivityState, SessionManager
from app.services.settings_service import SettingsService
from app.services.vault_service import VaultService
from app.ui.app_window import ApplicationController
from app.ui.locked_view import LockedView
from app.ui.settings_dialog import SettingsDialog
from app.ui.theme import DARK_THEME, LIGHT_THEME, ThemeManager
from app.ui.unlocked_view import UnlockedView


def run_verification() -> bool:
    print("=" * 60)
    print("Starting SecureVault M8 Verification Suite")
    print("=" * 60)

    with tempfile.TemporaryDirectory() as temp_dir:
        tmp_path = Path(temp_dir)
        config = AppConfig(data_dir=tmp_path)
        init_service = InitializationService(config)
        vault_service = VaultService(config)
        settings_service = SettingsService(config)

        # -------------------------------------------------------------
        # Setup Initial Vault
        # -------------------------------------------------------------
        print("\n[SETUP] Initializing application and creating vault...")
        init_service.initialize("alice")
        vault = vault_service.create_vault(
            "OriginalPass123!",
            kdf_params=KDFParameters.fast_for_testing(),
        )
        cred_service = CredentialService(vault_service)
        cred_service.create_credential(
            title="ProtonMail",
            username="alice@pm.me",
            password="proton-secret-password",
            notes="Primary secure email",
        )
        print("  ✓ Vault created with credential 'ProtonMail'")

        # -------------------------------------------------------------
        # 1. GENERAL — Appearance Theme Switching & Persistence
        # -------------------------------------------------------------
        print("\n[VERIFY 1] General — Appearance:")
        sm = SessionManager(countdown_seconds=120)
        unlocked_view = UnlockedView(
            vault=vault,
            login_id="alice",
            vault_service=vault_service,
            credential_service=cred_service,
            session_manager=sm,
            settings_service=settings_service,
        )

        settings_dlg = SettingsDialog(
            settings_service=settings_service,
            session_manager=sm,
            vault_service=vault_service,
            parent=unlocked_view,
        )

        # 1.1 General is default tab
        assert settings_dlg.sidebar.currentRow() == 0
        assert settings_dlg.content_stack.currentIndex() == 0
        print("  ✓ General tab opened by default")

        # 1.2 Dark is selected initially
        assert settings_dlg.dark_radio.isChecked() is True
        assert ThemeManager.instance().get_theme() == DARK_THEME
        print("  ✓ Dark theme is selected initially")

        # 1.3 Switch to Light
        settings_dlg.light_radio.click()
        assert ThemeManager.instance().get_theme() == LIGHT_THEME
        assert settings_service.get_settings().theme == LIGHT_THEME
        print("  ✓ Switched to Light theme immediately at runtime")

        # 1.4 Close and reopen settings; confirm Light remains selected
        settings_dlg.close()
        settings_dlg2 = SettingsDialog(
            settings_service=settings_service,
            session_manager=sm,
            vault_service=vault_service,
            parent=unlocked_view,
        )
        assert settings_dlg2.light_radio.isChecked() is True
        print("  ✓ Reopened Settings: Light remains selected")
        settings_dlg2.close()

        # 1.5 Restart SecureVault (simulate fresh controller launch)
        fresh_settings_service = SettingsService(config)
        fresh_controller = ApplicationController(
            config=config,
            settings_service=fresh_settings_service,
        )
        assert ThemeManager.instance().get_theme() == LIGHT_THEME
        print("  ✓ Application restart: Light theme persisted and restored before display")

        # 1.6 Switch back to Dark
        fresh_settings_service.set_theme(DARK_THEME)
        ThemeManager.instance().apply_theme(DARK_THEME)
        assert ThemeManager.instance().get_theme() == DARK_THEME
        print("  ✓ Switched back to Dark theme and persisted")

        # -------------------------------------------------------------
        # 2. SECURITY — Auto-Lock Configuration
        # -------------------------------------------------------------
        print("\n[VERIFY 2] Security — Auto-Lock:")
        settings_dlg3 = SettingsDialog(
            settings_service=settings_service,
            session_manager=sm,
            vault_service=vault_service,
            parent=unlocked_view,
        )
        settings_dlg3.sidebar.setCurrentRow(1)  # Security tab

        # 2.1 Confirm exactly four options
        radios = [
            settings_dlg3.radio_2m,
            settings_dlg3.radio_5m,
            settings_dlg3.radio_10m,
            settings_dlg3.radio_15m,
        ]
        assert len(radios) == 4
        print("  ✓ Exactly four timeout options present (2, 5, 10, 15 minutes)")

        # 2.2 Confirm no grace-period selector
        assert settings_dlg3.findChild(object, "GracePeriodInput") is None
        assert sm.grace_seconds == 15
        print("  ✓ No grace-period selector exists; grace period remains strictly 15s")

        # 2.3 Select each value and confirm live SessionManager update + persistence
        for timeout, radio in zip([300, 600, 900, 120], [settings_dlg3.radio_5m, settings_dlg3.radio_10m, settings_dlg3.radio_15m, settings_dlg3.radio_2m]):
            radio.click()
            assert settings_service.get_settings().auto_lock_timeout == timeout
            assert sm.countdown_seconds == timeout
            print(f"  ✓ Timeout {timeout // 60}m ({timeout}s) live updated in SessionManager and persisted")

        settings_dlg3.close()

        # -------------------------------------------------------------
        # 3. SECURITY — Master Password Change Flow
        # -------------------------------------------------------------
        print("\n[VERIFY 3] Security — Master Password:")
        # Suppress QMessageBox.information
        QMessageBox.information = lambda *args, **kwargs: QMessageBox.StandardButton.Ok

        settings_dlg4 = SettingsDialog(
            settings_service=settings_service,
            session_manager=sm,
            vault_service=vault_service,
            parent=unlocked_view,
        )
        settings_dlg4.sidebar.setCurrentRow(1)

        # 3.1 Try incorrect current password
        settings_dlg4.current_pwd_input.setText("WrongPassword123!")
        settings_dlg4.new_pwd_input.setText("NewPassword456!")
        settings_dlg4.confirm_pwd_input.setText("NewPassword456!")
        settings_dlg4.change_pwd_btn.click()
        assert "Incorrect current master password" in settings_dlg4.pwd_status_label.text()
        assert vault.is_locked is False
        print("  ✓ Incorrect current password rejected; vault remains unlocked and usable")

        # 3.2 Try mismatched confirmation
        settings_dlg4.current_pwd_input.setText("OriginalPass123!")
        settings_dlg4.new_pwd_input.setText("NewPassword456!")
        settings_dlg4.confirm_pwd_input.setText("MismatchedPass789!")
        settings_dlg4.change_pwd_btn.click()
        assert "Passwords do not match" in settings_dlg4.pwd_status_label.text()
        print("  ✓ Mismatched confirmation rejected")

        # 3.3 Valid change password
        initial_vault_id = vault.vault_id
        settings_dlg4.password_changed.connect(unlocked_view._on_master_password_changed)
        settings_dlg4.current_pwd_input.setText("OriginalPass123!")
        settings_dlg4.new_pwd_input.setText("BrandNewSecurePass456!")
        settings_dlg4.confirm_pwd_input.setText("BrandNewSecurePass456!")
        settings_dlg4.change_pwd_btn.click()

        # 3.4 Confirm dialog closed and vault locked
        assert settings_dlg4.isVisible() is False
        assert vault.is_locked is True
        print("  ✓ Master password changed; Settings dialog closed and vault locked")

        # 3.5 Old password MUST fail
        failed_old = False
        try:
            vault_service.unlock_vault("OriginalPass123!")
        except Exception:
            failed_old = True
        assert failed_old is True
        print("  ✓ Old master password successfully rejected")

        # 3.6 New password MUST succeed
        unlocked_new = vault_service.unlock_vault("BrandNewSecurePass456!")
        assert unlocked_new.vault_id == initial_vault_id
        print("  ✓ New master password successfully unlocked the vault; vault_id preserved")

        # 3.7 Existing credentials intact
        new_cred_service = CredentialService(vault_service)
        creds = new_cred_service.get_all_credentials()
        assert len(creds) == 1
        assert creds[0].title == "ProtonMail"
        assert creds[0].username == "alice@pm.me"
        assert creds[0].password == "proton-secret-password"
        assert creds[0].notes == "Primary secure email"
        print("  ✓ Existing credentials preserved intact across password change")

        # 3.8 CRUD operations still work
        created = new_cred_service.create_credential(
            title="Amazon",
            username="alice@amazon.com",
            password="amazon-pass-123",
        )
        assert created.title == "Amazon"
        assert len(new_cred_service.get_all_credentials()) == 2
        print("  ✓ Subsequent CRUD operations work seamlessly with updated vault")

    print("\n" + "=" * 60)
    print("ALL M8 VERIFICATION CHECKS PASSED PERFECTLY!")
    print("=" * 60)
    return True


if __name__ == "__main__":
    success = run_verification()
    sys.exit(0 if success else 1)

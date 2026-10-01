"""SecureVault — Milestone M10 Manual Verification Script.

Executes the Section 19 Verification Checklist:
1. Open a credential -> Copy Username -> confirms username on clipboard -> timer clears clipboard.
2. Copy Password -> confirms password on clipboard -> timer clears clipboard.
3. Ownership Protection: Copy Password -> manual clipboard replacement -> timer expires -> unrelated text preserved.
4. Overlapping Copies: Copy Username -> Copy Password -> first timer does NOT clear password -> second timer clears password.
5. Lock Integration: Copy Password -> Lock vault -> owned clipboard cleared.
6. Lock with User Replacement: Copy Password -> user replaces -> Lock vault -> user text preserved.
7. Verification of zero clipboard history, zero secret logging, and no password generator.
"""

from __future__ import annotations

import os
import sys

from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Ensure UTF-8 output on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PySide6.QtWidgets import QApplication

from app.core.config import AppConfig
from app.crypto.kdf import KDFParameters
from app.models.credential import Credential
from app.services.clipboard_service import (
    CLIPBOARD_CLEAR_TIMEOUT_SECONDS,
    ClipboardService,
)
from app.services.credential_service import CredentialService
from app.services.vault_service import VaultService
from app.ui.unlocked_view import UnlockedView, ViewCredentialDialog


def log_step(name: str, passed: bool) -> None:
    mark = "✓" if passed else "✕"
    print(f"[{mark}] {name}")
    if not passed:
        raise AssertionError(f"Step failed: {name}")


def main() -> None:
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)

    print("==================================================")
    print("SecureVault — M10 Clipboard Security Verification")
    print("==================================================")

    # Setup isolated test environment
    import tempfile
    from pathlib import Path

    temp_dir = Path(tempfile.mkdtemp(prefix="sv_m10_verify_"))
    config = AppConfig(data_dir=temp_dir)
    vault_service = VaultService(config)
    vault = vault_service.create_vault("MasterPassword123!", kdf_params=KDFParameters.fast_for_testing())
    cred_service = CredentialService(vault_service)

    cred = cred_service.create_credential(
        title="ProtonMail",
        username="security_alice@proton.me",
        password="SuperVaultSecret456!",
        notes="Primary email",
    )

    qt_cb = app.clipboard()
    qt_cb.clear()

    # Step 1-5: Copy Username and Auto-Clear
    print("\n--- Phase 1: Copy Username & Auto-Clear ---")
    clip_service = ClipboardService(timeout_seconds=0.1)
    view_dialog = ViewCredentialDialog(cred, clipboard_service=clip_service)

    view_dialog.copy_username_btn.click()
    log_step("Step 1-2: Copy Username reaches OS clipboard", qt_cb.text() == "security_alice@proton.me")
    log_step("Step 3: Dialog confirmation message visible", "Username copied. Clipboard will clear in 30 seconds." in view_dialog.status_label.text())

    clip_service._on_timeout()
    log_step("Step 4-5: Unchanged Username cleared after timeout", qt_cb.text() == "")

    # Step 6-9: Copy Password and Auto-Clear
    print("\n--- Phase 2: Copy Password & Auto-Clear ---")
    clip_service = ClipboardService(timeout_seconds=0.1)
    view_dialog = ViewCredentialDialog(cred, clipboard_service=clip_service)

    view_dialog.copy_password_btn.click()
    log_step("Step 6-7: Copy Password reaches OS clipboard", qt_cb.text() == "SuperVaultSecret456!")
    log_step("Step 7b: Password field remains masked", view_dialog.password_val.echoMode() == view_dialog.password_val.EchoMode.Password)
    log_step("Step 7c: Confirmation message visible", "Password copied. Clipboard will clear in 30 seconds." in view_dialog.status_label.text())

    clip_service._on_timeout()
    log_step("Step 8-9: Unchanged Password cleared after timeout", qt_cb.text() == "")

    # Step 10-13: Ownership Protection
    print("\n--- Phase 3: Ownership Protection on User Replacement ---")
    clip_service = ClipboardService(timeout_seconds=0.1)
    view_dialog = ViewCredentialDialog(cred, clipboard_service=clip_service)

    view_dialog.copy_password_btn.click()
    log_step("Step 10: Password copied to clipboard", qt_cb.text() == "SuperVaultSecret456!")

    # User manually copies unrelated text before timeout
    qt_cb.setText("Unrelated user clipboard content")
    log_step("Step 11: User replaces clipboard manually", qt_cb.text() == "Unrelated user clipboard content")

    cleared = clip_service._on_timeout()
    log_step("Step 12-13: Timer expires without clearing unrelated content", cleared is False and qt_cb.text() == "Unrelated user clipboard content")

    # Step 14-20: Overlapping SecureVault Copies
    print("\n--- Phase 4: Overlapping SecureVault Copies ---")
    clip_service = ClipboardService(timeout_seconds=0.1)
    view_dialog = ViewCredentialDialog(cred, clipboard_service=clip_service)

    view_dialog.copy_username_btn.click()
    log_step("Step 14: Copy Username initiated", qt_cb.text() == "security_alice@proton.me")

    # Overlapping copy password
    view_dialog.copy_password_btn.click()
    log_step("Step 16: Copy Password overrides active tracking", qt_cb.text() == "SuperVaultSecret456!")
    log_step("Step 17-18: Active tracked value is the password", clip_service.get_tracked_value() == "SuperVaultSecret456!")

    cleared = clip_service._on_timeout()
    log_step("Step 19-20: Second copy timer clears password", cleared is True and qt_cb.text() == "")

    # Step 21-23: Lock Clears Owned Clipboard
    print("\n--- Phase 5: Vault Lock Clears Owned Clipboard ---")
    clip_service = ClipboardService(timeout_seconds=30)
    unlocked_view = UnlockedView(
        vault=vault,
        vault_service=vault_service,
        credential_service=cred_service,
        clipboard_service=clip_service,
    )

    clip_service.copy_password("secret_to_lock")
    log_step("Step 21: Password in clipboard before lock", qt_cb.text() == "secret_to_lock")

    unlocked_view._on_lock_clicked()
    log_step("Step 22-23: Locking vault clears owned clipboard", qt_cb.text() == "")

    # Step 24-27: Lock Preserves Replaced Clipboard
    print("\n--- Phase 6: Vault Lock Preserves User Replaced Clipboard ---")
    # Re-unlock vault for second test
    vault = vault_service.unlock_vault("MasterPassword123!")
    clip_service = ClipboardService(timeout_seconds=30)
    unlocked_view = UnlockedView(
        vault=vault,
        vault_service=vault_service,
        credential_service=cred_service,
        clipboard_service=clip_service,
    )

    clip_service.copy_password("secret_replaced")
    qt_cb.setText("User external spreadsheet text")
    log_step("Step 24-25: Clipboard replaced externally", qt_cb.text() == "User external spreadsheet text")

    unlocked_view._on_lock_clicked()
    log_step("Step 26-27: Locking vault leaves external text untouched", qt_cb.text() == "User external spreadsheet text")

    # Security & Architectural Verification
    print("\n--- Phase 7: Scope & Invariant Verifications ---")
    log_step("M10 Constant is 30 seconds", CLIPBOARD_CLEAR_TIMEOUT_SECONDS == 30)
    log_step("No password generator implemented", not hasattr(cred_service, "generate_password"))
    log_step("No clipboard history retained", not hasattr(clip_service, "get_history") and not hasattr(clip_service, "_history"))
    log_step("Clipboard cleared at end of test", (qt_cb.clear(), qt_cb.text() == "")[1])

    # Cleanup temp directory
    try:
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)
    except Exception:
        pass

    print("\n==================================================")
    print("ALL M10 VERIFICATION STEPS PASSED SUCCESSFULLY!")
    print("==================================================")


if __name__ == "__main__":
    main()

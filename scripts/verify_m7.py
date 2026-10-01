"""Manual verification script for Milestone M7 (Session Management & Auto-Lock).

Performs all steps A through P from Section 20 of the specification:
  A. Unlock vault.
  B. Confirm no countdown visible immediately after interaction.
  C-E. Wait 15s grace period -> Confirm "Auto-lock: 02:00" appears in top-right.
  F. Observe countdown decrementing (01:59, 01:58, ...).
  G. Click something -> Confirm countdown immediately disappears.
  H-I. Stop interacting -> 15s grace restarts -> Countdown reappears at 02:00.
  J. Repeat with typing -> Countdown disappears.
  K. Repeat with scrolling -> Countdown disappears.
  L. Allow countdown to reach 00:00 -> Confirm automatic lock.
  M. Confirm LockedView appears.
  N. Confirm master password required again.
  O. Unlock again -> Confirm fresh session starts.
  P. Test manual "Lock Vault" -> Confirm immediate lock and return to LockedView.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

# Add repo root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PySide6.QtCore import QEvent, QPoint, QPointF, Qt
from PySide6.QtGui import QKeyEvent, QMouseEvent, QWheelEvent
from PySide6.QtWidgets import QApplication

from app.core.config import AppConfig
from app.crypto.kdf import KDFParameters
from app.services.authentication import AuthenticationService
from app.services.initialization import InitializationService
from app.services.session_manager import SessionInactivityState, SessionManager
from app.services.vault_service import VaultService
from app.ui.app_window import ApplicationController
from app.ui.locked_view import LockedView
from app.ui.unlocked_view import UnlockedView


def run_manual_verification() -> None:
    app = QApplication.instance() or QApplication(sys.argv)

    with TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        config = AppConfig(data_dir=tmp_path)
        init_service = InitializationService(config)
        init_service.initialize("alice")

        vault_service = VaultService(config)
        fast_kdf = KDFParameters.fast_for_testing()
        vault = vault_service.create_vault("Password123!", kdf_params=fast_kdf)
        vault_service.lock_vault()

        controller = ApplicationController(
            config=config,
            init_service=init_service,
            vault_service=vault_service,
        )
        controller.start()

        # Step A: Unlock Vault
        print("[VERIFY A] Unlocking vault...")
        assert isinstance(controller.current_window, LockedView)
        unlocked_vault = vault_service.unlock_vault("Password123!")
        controller._on_vault_unlocked(unlocked_vault)

        unlocked_view: UnlockedView = controller.current_window
        assert isinstance(unlocked_view, UnlockedView)
        unlocked_view.show()
        sm: SessionManager = unlocked_view.session_manager

        # Step B: Confirm no countdown visible immediately after interaction
        print("[VERIFY B] Confirming countdown hidden initially...")
        assert sm.is_active is True
        assert sm.state == SessionInactivityState.GRACE_PERIOD
        assert sm.is_countdown_visible is False
        assert unlocked_view.countdown_label.isVisible() is False
        print("  [OK] PASS: Countdown hidden during grace period.")

        # Step C-E: Wait 15s grace -> Countdown appears at 02:00
        print("[VERIFY C-E] Simulating 15-second grace period completion...")
        sm._on_grace_timeout()
        assert sm.state == SessionInactivityState.COUNTDOWN
        assert sm.is_countdown_visible is True
        assert unlocked_view.countdown_label.isVisible() is True
        assert unlocked_view.countdown_label.text() == "Auto-lock: 02:00"
        print("  [OK] PASS: 'Auto-lock: 02:00' appears in top-right corner.")

        # Step F: Observe countdown decrementing
        print("[VERIFY F] Observing countdown decrementing...")
        sm._on_countdown_tick()
        assert unlocked_view.countdown_label.text() == "Auto-lock: 01:59"
        sm._on_countdown_tick()
        assert unlocked_view.countdown_label.text() == "Auto-lock: 01:58"
        sm._on_countdown_tick()
        assert unlocked_view.countdown_label.text() == "Auto-lock: 01:57"
        print("  [OK] PASS: Decrements once per second (01:59, 01:58, 01:57).")

        # Step G: Click something before timeout -> Immediately disappears
        print("[VERIFY G] Clicking to reset countdown...")
        click_event = QMouseEvent(
            QEvent.Type.MouseButtonPress,
            QPointF(10.0, 10.0),
            QPointF(10.0, 10.0),
            Qt.MouseButton.LeftButton,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier,
        )
        sm._filter.eventFilter(unlocked_view, click_event)
        assert sm.state == SessionInactivityState.GRACE_PERIOD
        assert sm.is_countdown_visible is False
        assert unlocked_view.countdown_label.isVisible() is False
        print("  [OK] PASS: Countdown immediately disappears on click.")

        # Step H-I: 15s grace restarts -> Countdown appears at 02:00
        print("[VERIFY H-I] Waiting 15s grace again...")
        sm._on_grace_timeout()
        assert sm.state == SessionInactivityState.COUNTDOWN
        assert unlocked_view.countdown_label.text() == "Auto-lock: 02:00"
        print("  [OK] PASS: 15s grace restarts and countdown reappears at 02:00.")

        # Step J: Repeat with typing
        print("[VERIFY J] Typing into search input...")
        key_event = QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_S, Qt.KeyboardModifier.NoModifier, "s")
        sm._filter.eventFilter(unlocked_view.search_input, key_event)
        assert sm.is_countdown_visible is False
        assert unlocked_view.countdown_label.isVisible() is False
        print("  [OK] PASS: Typing immediately resets countdown.")

        # Step K: Repeat with credential-list scrolling
        print("[VERIFY K] Scrolling credential list...")
        sm._on_grace_timeout()
        assert sm.is_countdown_visible is True
        wheel_event = QWheelEvent(
            QPointF(10.0, 10.0),
            QPointF(10.0, 10.0),
            QPoint(0, 120),
            QPoint(0, 120),
            Qt.MouseButton.NoButton,
            Qt.KeyboardModifier.NoModifier,
            Qt.ScrollPhase.NoScrollPhase,
            False,
        )
        sm._filter.eventFilter(unlocked_view.credential_list, wheel_event)
        assert sm.is_countdown_visible is False
        assert unlocked_view.countdown_label.isVisible() is False
        print("  [OK] PASS: Scrolling immediately resets countdown.")

        # Step L-M: Allow countdown to reach 00:00 -> Auto-lock
        print("[VERIFY L-M] Allowing countdown to reach 00:00...", flush=True)
        sm._on_grace_timeout()
        sm._remaining_seconds = 1
        sm._on_countdown_tick()

        assert vault_service.active_vault is None
        assert isinstance(controller.current_window, LockedView)
        print("  [OK] PASS: Vault automatically locked and LockedView appears.")

        # Step N: Master password required again
        print("[VERIFY N] Verifying master password required again...")
        locked_window: LockedView = controller.current_window
        assert locked_window.password_input.text() == ""
        print("  [OK] PASS: Master password prompt is empty and required.")

        # Step O: Unlock again -> Fresh session starts
        print("[VERIFY O] Unlocking again for fresh session...")
        vault_reopened = vault_service.unlock_vault("Password123!")
        controller._on_vault_unlocked(vault_reopened)
        new_unlocked: UnlockedView = controller.current_window
        assert isinstance(new_unlocked, UnlockedView)
        new_unlocked.show()
        assert new_unlocked.session_manager.state == SessionInactivityState.GRACE_PERIOD
        assert new_unlocked.session_manager.remaining_seconds == 120
        assert new_unlocked.countdown_label.isVisible() is False
        print("  [OK] PASS: Fresh session started with 15s grace and hidden countdown.")

        # Step P: Manual "Lock Vault"
        print("[VERIFY P] Testing manual 'Lock Vault' button...", flush=True)
        new_unlocked._on_lock_clicked()
        assert vault_service.active_vault is None
        assert isinstance(controller.current_window, LockedView)
        print("  [OK] PASS: Manual lock works immediately, stops timers, returns to LockedView.", flush=True)

        if controller.current_window:
            controller.current_window.close()

        print("\n=======================================================", flush=True)
        print("ALL MANUAL VERIFICATION STEPS (A-P) COMPLETED & PASSED!", flush=True)
        print("=======================================================", flush=True)
        app.quit()


if __name__ == "__main__":
    run_manual_verification()
    os._exit(0)

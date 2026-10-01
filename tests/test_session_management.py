"""SecureVault — Milestone M7 Session Management & Auto-Lock Tests.

Comprehensive automated verification of:
  1. Session starts when vault becomes unlocked.
  2. Session is inactive during LockedView.
  3. Typing resets inactivity.
  4. Clicking resets inactivity.
  5. Scrolling resets inactivity.
  6. Mouse movement alone does NOT reset inactivity.
  7. Countdown is hidden during active interaction.
  8. Countdown remains hidden during first 15 seconds (grace period).
  9. Countdown becomes visible after 15 seconds.
  10. Countdown begins at exactly 02:00.
  11. Countdown decrements once per second.
  12. Interaction during countdown hides it immediately.
  13. Interaction during countdown resets it to the 15-second grace period.
  14. Countdown reaches 00:00.
  15. Automatic lock occurs at timeout.
  16. Automatic lock uses the existing lock mechanism.
  17. Manual Lock immediately cancels the timers.
  18. Manual Lock hides the countdown.
  19. Unlocking starts a fresh session.
  20. Locking stops all timers.
  21. Application close stops/cleans up timers.
  22. Search typing resets inactivity.
  23. Credential list scrolling resets inactivity.
  24. View/Edit/Delete interaction resets inactivity.
  25. No sensitive data is stored inside the session timer/controller.
  26. Edge cases: rapid interactions, modal dialogs closed on auto-lock, format_time.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from PySide6.QtCore import QEvent, QPoint, QPointF, Qt
from PySide6.QtGui import QKeyEvent, QMouseEvent, QWheelEvent
from PySide6.QtWidgets import QApplication, QDialog, QLabel, QLineEdit

os.environ["QT_QPA_PLATFORM"] = "offscreen"


@pytest.fixture(scope="session")
def qapp() -> QApplication:
    """Ensure a singleton QApplication exists for GUI tests."""
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    return app

from app.core.config import (
    ACTIVITY_GRACE_SECONDS,
    INACTIVITY_TIMEOUT_SECONDS,
    AppConfig,
)
from app.crypto.kdf import KDFParameters
from app.services.authentication import AuthenticationService
from app.services.credential_service import CredentialService
from app.services.initialization import InitializationService
from app.services.session_manager import (
    ActivityEventFilter,
    SessionInactivityState,
    SessionManager,
)
from app.services.vault_service import DecryptedVault, VaultService
from app.ui.app_window import ApplicationController
from app.ui.locked_view import LockedView
from app.ui.unlocked_view import UnlockedView


@pytest.fixture
def fast_vault_service(tmp_path: Path) -> VaultService:
    """VaultService configured with fast KDF for rapid test execution."""
    config = AppConfig(data_dir=tmp_path)
    return VaultService(config)


@pytest.fixture
def unlocked_setup(fast_vault_service: VaultService) -> tuple[DecryptedVault, VaultService, CredentialService]:
    """Create and unlock a valid test vault."""
    fast_kdf = KDFParameters.fast_for_testing()
    vault = fast_vault_service.create_vault(
        master_password="MasterTestPassword123!",
        kdf_params=fast_kdf,
    )
    cred_service = CredentialService(fast_vault_service)
    return vault, fast_vault_service, cred_service


# =========================================================================
# 1. Session Lifecycle & State Initialization Tests
# =========================================================================

def test_session_starts_when_vault_becomes_unlocked(qapp: QApplication, unlocked_setup) -> None:
    """1. Session starts when vault becomes unlocked."""
    vault, vault_service, cred_service = unlocked_setup
    sm = SessionManager(grace_seconds=15, countdown_seconds=120)

    view = UnlockedView(
        vault=vault,
        login_id="alice",
        vault_service=vault_service,
        credential_service=cred_service,
        session_manager=sm,
    )

    sm.start_session()
    assert sm.is_active is True
    assert sm.state == SessionInactivityState.GRACE_PERIOD
    assert sm.is_countdown_visible is False
    assert sm.remaining_seconds == 120
    sm.stop_session()


def test_session_is_inactive_during_locked_view(qapp: QApplication, tmp_path: Path) -> None:
    """2. Session is inactive during LockedView."""
    config = AppConfig(data_dir=tmp_path)
    init_service = InitializationService(config)
    init_service.initialize("test_user")

    controller = ApplicationController(config=config, init_service=init_service)
    controller.start()

    assert isinstance(controller.current_window, LockedView)
    # LockedView has no session manager active
    assert not hasattr(controller.current_window, "session_manager")


# =========================================================================
# 2. Activity Detection & Reset Tests (Typing, Clicking, Scrolling)
# =========================================================================

def test_typing_resets_inactivity(qapp: QApplication) -> None:
    """3. Typing resets inactivity."""
    activity_count = 0

    def on_act():
        nonlocal activity_count
        activity_count += 1

    sm = SessionManager(grace_seconds=15, countdown_seconds=120)
    sm.activity_detected.connect(on_act)
    sm.start_session()

    # Move to countdown state to verify reset
    sm._on_grace_timeout()
    assert sm.state == SessionInactivityState.COUNTDOWN
    assert sm.is_countdown_visible is True

    # Simulate key press event
    key_event = QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_A, Qt.KeyboardModifier.NoModifier, "a")
    sm._filter.eventFilter(qapp, key_event)

    assert sm.state == SessionInactivityState.GRACE_PERIOD
    assert sm.is_countdown_visible is False
    assert sm.remaining_seconds == 120
    assert activity_count == 1
    sm.stop_session()


def test_clicking_resets_inactivity(qapp: QApplication) -> None:
    """4. Clicking resets inactivity."""
    activity_count = 0

    def on_act():
        nonlocal activity_count
        activity_count += 1

    sm = SessionManager(grace_seconds=15, countdown_seconds=120)
    sm.activity_detected.connect(on_act)
    sm.start_session()

    sm._on_grace_timeout()
    assert sm.state == SessionInactivityState.COUNTDOWN

    # Simulate mouse click
    mouse_event = QMouseEvent(
        QEvent.Type.MouseButtonPress,
        QPointF(10.0, 10.0),
        QPointF(10.0, 10.0),
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    sm._filter.eventFilter(qapp, mouse_event)

    assert sm.state == SessionInactivityState.GRACE_PERIOD
    assert sm.is_countdown_visible is False
    assert sm.remaining_seconds == 120
    assert activity_count == 1
    sm.stop_session()


def test_scrolling_resets_inactivity(qapp: QApplication) -> None:
    """5. Scrolling resets inactivity."""
    activity_count = 0

    def on_act():
        nonlocal activity_count
        activity_count += 1

    sm = SessionManager(grace_seconds=15, countdown_seconds=120)
    sm.activity_detected.connect(on_act)
    sm.start_session()

    sm._on_grace_timeout()
    assert sm.state == SessionInactivityState.COUNTDOWN

    # Simulate wheel scroll event
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
    sm._filter.eventFilter(qapp, wheel_event)

    assert sm.state == SessionInactivityState.GRACE_PERIOD
    assert sm.is_countdown_visible is False
    assert sm.remaining_seconds == 120
    assert activity_count == 1
    sm.stop_session()


def test_mouse_movement_alone_does_not_reset_inactivity(qapp: QApplication) -> None:
    """6. Mouse movement alone does NOT reset inactivity."""
    activity_count = 0

    def on_act():
        nonlocal activity_count
        activity_count += 1

    sm = SessionManager(grace_seconds=15, countdown_seconds=120)
    sm.activity_detected.connect(on_act)
    sm.start_session()

    sm._on_grace_timeout()
    assert sm.state == SessionInactivityState.COUNTDOWN
    assert sm.is_countdown_visible is True

    # Simulate mouse move event
    move_event = QMouseEvent(
        QEvent.Type.MouseMove,
        QPointF(20.0, 20.0),
        QPointF(20.0, 20.0),
        Qt.MouseButton.NoButton,
        Qt.MouseButton.NoButton,
        Qt.KeyboardModifier.NoModifier,
    )
    sm._filter.eventFilter(qapp, move_event)

    # State must remain COUNTDOWN, visible, and activity NOT fired
    assert sm.state == SessionInactivityState.COUNTDOWN
    assert sm.is_countdown_visible is True
    assert activity_count == 0
    sm.stop_session()


# =========================================================================
# 3. Countdown Timing, Visibility & UI Tests
# =========================================================================

def test_countdown_hidden_during_active_interaction(qapp: QApplication, unlocked_setup) -> None:
    """7. Countdown is hidden during active interaction."""
    vault, vault_service, cred_service = unlocked_setup
    sm = SessionManager(grace_seconds=15, countdown_seconds=120)

    view = UnlockedView(
        vault=vault,
        login_id="alice",
        vault_service=vault_service,
        credential_service=cred_service,
        session_manager=sm,
    )
    sm.start_session()

    assert view.countdown_label.isVisible() is False
    sm.reset_activity()
    assert view.countdown_label.isVisible() is False
    sm.stop_session()


def test_countdown_remains_hidden_during_first_15_seconds(qapp: QApplication) -> None:
    """8. Countdown remains hidden during first 15 seconds."""
    sm = SessionManager(grace_seconds=15, countdown_seconds=120)
    visibility_events = []
    sm.countdown_visibility_changed.connect(visibility_events.append)

    sm.start_session()
    assert sm.state == SessionInactivityState.GRACE_PERIOD
    assert sm.is_countdown_visible is False
    assert visibility_events == [False]
    sm.stop_session()


def test_countdown_becomes_visible_after_15_seconds(qapp: QApplication) -> None:
    """9. Countdown becomes visible after 15 seconds."""
    sm = SessionManager(grace_seconds=15, countdown_seconds=120)
    visibility_events = []
    sm.countdown_visibility_changed.connect(visibility_events.append)

    sm.start_session()
    assert sm.is_countdown_visible is False

    # Simulate 15-second grace expiration
    sm._on_grace_timeout()
    assert sm.state == SessionInactivityState.COUNTDOWN
    assert sm.is_countdown_visible is True
    assert visibility_events[-1] is True
    sm.stop_session()


def test_countdown_begins_at_exactly_02_00(qapp: QApplication, unlocked_setup) -> None:
    """10. Countdown begins at exactly 02:00."""
    vault, vault_service, cred_service = unlocked_setup
    sm = SessionManager(grace_seconds=15, countdown_seconds=120)

    view = UnlockedView(
        vault=vault,
        login_id="alice",
        vault_service=vault_service,
        credential_service=cred_service,
        session_manager=sm,
    )
    sm.start_session()

    sm._on_grace_timeout()
    assert view.countdown_label.text() == "Auto-lock: 02:00"
    assert sm.remaining_seconds == 120
    sm.stop_session()


def test_countdown_decrements_once_per_second(qapp: QApplication) -> None:
    """11. Countdown decrements once per second."""
    sm = SessionManager(grace_seconds=15, countdown_seconds=120)
    ticks = []
    sm.countdown_updated.connect(lambda secs, text: ticks.append((secs, text)))

    sm.start_session()
    sm._on_grace_timeout()

    assert sm.remaining_seconds == 120
    sm._on_countdown_tick()
    assert sm.remaining_seconds == 119
    assert ticks[-1] == (119, "Auto-lock: 01:59")

    sm._on_countdown_tick()
    assert sm.remaining_seconds == 118
    assert ticks[-1] == (118, "Auto-lock: 01:58")
    sm.stop_session()


def test_interaction_during_countdown_hides_it_immediately(qapp: QApplication, unlocked_setup) -> None:
    """12. Interaction during countdown hides it immediately."""
    vault, vault_service, cred_service = unlocked_setup
    sm = SessionManager(grace_seconds=15, countdown_seconds=120)

    view = UnlockedView(
        vault=vault,
        login_id="alice",
        vault_service=vault_service,
        credential_service=cred_service,
        session_manager=sm,
    )
    view.show()
    sm.start_session()
    sm._on_grace_timeout()

    assert view.countdown_label.isVisible() is True

    # User clicks
    sm.reset_activity()
    assert view.countdown_label.isVisible() is False
    assert sm.is_countdown_visible is False
    sm.stop_session()


def test_interaction_during_countdown_resets_to_15_second_grace(qapp: QApplication) -> None:
    """13. Interaction during countdown resets it to the 15-second grace period."""
    sm = SessionManager(grace_seconds=15, countdown_seconds=120)
    sm.start_session()
    sm._on_grace_timeout()

    # Tick a few times
    sm._on_countdown_tick()
    sm._on_countdown_tick()
    assert sm.remaining_seconds == 118

    # Reset activity
    sm.reset_activity()
    assert sm.state == SessionInactivityState.GRACE_PERIOD
    assert sm.remaining_seconds == 120
    assert sm.is_countdown_visible is False
    sm.stop_session()


def test_countdown_reaches_00_00(qapp: QApplication) -> None:
    """14. Countdown reaches 00:00."""
    sm = SessionManager(grace_seconds=15, countdown_seconds=2)
    history = []
    sm.countdown_updated.connect(lambda secs, txt: history.append((secs, txt)))

    sm.start_session()
    sm._on_grace_timeout()

    sm._on_countdown_tick()  # 1 sec remaining
    assert sm.remaining_seconds == 1
    assert history[-1] == (1, "Auto-lock: 00:01")

    sm._on_countdown_tick()  # 0 sec remaining
    assert sm.remaining_seconds == 0
    assert history[-1] == (0, "Auto-lock: 00:00")
    sm.stop_session()


# =========================================================================
# 4. Automatic Lock & Manual Lock Tests
# =========================================================================

def test_automatic_lock_occurs_at_timeout(qapp: QApplication, unlocked_setup) -> None:
    """15. Automatic lock occurs at timeout."""
    vault, vault_service, cred_service = unlocked_setup
    sm = SessionManager(grace_seconds=15, countdown_seconds=1)

    view = UnlockedView(
        vault=vault,
        login_id="alice",
        vault_service=vault_service,
        credential_service=cred_service,
        session_manager=sm,
    )
    sm.start_session()
    sm._on_grace_timeout()

    lock_events = []
    view.lock_requested.connect(lambda: lock_events.append(True))

    # Tick to 00:00
    sm._on_countdown_tick()

    assert sm.state == SessionInactivityState.LOCKED
    assert len(lock_events) == 1
    assert vault.is_locked is True


def test_automatic_lock_uses_existing_lock_mechanism(qapp: QApplication, unlocked_setup) -> None:
    """16. Automatic lock uses the existing lock mechanism."""
    vault, vault_service, cred_service = unlocked_setup
    sm = SessionManager(grace_seconds=15, countdown_seconds=1)

    view = UnlockedView(
        vault=vault,
        login_id="alice",
        vault_service=vault_service,
        credential_service=cred_service,
        session_manager=sm,
    )
    sm.start_session()
    sm._on_grace_timeout()

    # Before lock: DEK is populated
    assert any(b != 0 for b in vault.dek)
    assert vault.is_locked is False

    # Auto-lock
    sm._on_countdown_tick()

    # After lock: DEK zeroed, vault locked
    assert all(b == 0 for b in vault.dek)
    assert vault.is_locked is True
    assert vault.item_count == 0


def test_manual_lock_immediately_cancels_timers(qapp: QApplication, unlocked_setup) -> None:
    """17. Manual Lock immediately cancels the timers."""
    vault, vault_service, cred_service = unlocked_setup
    sm = SessionManager(grace_seconds=15, countdown_seconds=120)

    view = UnlockedView(
        vault=vault,
        login_id="alice",
        vault_service=vault_service,
        credential_service=cred_service,
        session_manager=sm,
    )
    sm.start_session()

    view._on_lock_clicked()

    assert sm.state == SessionInactivityState.INACTIVE
    assert sm.is_active is False
    assert sm._grace_timer.isActive() is False
    assert sm._countdown_timer.isActive() is False


def test_manual_lock_hides_countdown(qapp: QApplication, unlocked_setup) -> None:
    """18. Manual Lock hides the countdown."""
    vault, vault_service, cred_service = unlocked_setup
    sm = SessionManager(grace_seconds=15, countdown_seconds=120)

    view = UnlockedView(
        vault=vault,
        login_id="alice",
        vault_service=vault_service,
        credential_service=cred_service,
        session_manager=sm,
    )
    view.show()
    sm.start_session()
    sm._on_grace_timeout()
    assert view.countdown_label.isVisible() is True

    view._on_lock_clicked()
    assert view.countdown_label.isVisible() is False
    assert sm.is_countdown_visible is False


def test_unlocking_starts_fresh_session(qapp: QApplication, fast_vault_service: VaultService) -> None:
    """19. Unlocking starts a fresh session."""
    fast_kdf = KDFParameters.fast_for_testing()
    vault = fast_vault_service.create_vault("MasterTestPassword123!", kdf_params=fast_kdf)

    sm = SessionManager(grace_seconds=15, countdown_seconds=120)
    view1 = UnlockedView(vault=vault, login_id="alice", vault_service=fast_vault_service, session_manager=sm)
    sm.start_session()
    sm._on_grace_timeout()
    assert sm.state == SessionInactivityState.COUNTDOWN

    view1._on_lock_clicked()
    assert sm.state == SessionInactivityState.INACTIVE

    # Re-unlock
    vault2 = fast_vault_service.unlock_vault("MasterTestPassword123!")
    sm2 = SessionManager(grace_seconds=15, countdown_seconds=120)
    view2 = UnlockedView(vault=vault2, login_id="alice", vault_service=fast_vault_service, session_manager=sm2)
    sm2.start_session()

    assert sm2.state == SessionInactivityState.GRACE_PERIOD
    assert sm2.remaining_seconds == 120
    assert view2.countdown_label.isVisible() is False
    sm2.stop_session()


def test_locking_stops_all_timers(qapp: QApplication) -> None:
    """20. Locking stops all timers."""
    sm = SessionManager(grace_seconds=15, countdown_seconds=120)
    sm.start_session()

    assert sm._grace_timer.isActive() is True
    sm.stop_session()

    assert sm._grace_timer.isActive() is False
    assert sm._countdown_timer.isActive() is False


def test_application_close_stops_cleanups_timers(qapp: QApplication, unlocked_setup) -> None:
    """21. Application close stops/cleans up timers."""
    vault, vault_service, cred_service = unlocked_setup
    sm = SessionManager(grace_seconds=15, countdown_seconds=120)

    view = UnlockedView(
        vault=vault,
        login_id="alice",
        vault_service=vault_service,
        credential_service=cred_service,
        session_manager=sm,
    )
    sm.start_session()
    assert sm.is_active is True

    view.close()
    assert sm.is_active is False
    assert sm._grace_timer.isActive() is False
    assert sm._countdown_timer.isActive() is False


# =========================================================================
# 5. UI Control Interaction Tests
# =========================================================================

def test_search_typing_resets_inactivity(qapp: QApplication, unlocked_setup) -> None:
    """22. Search typing resets inactivity."""
    vault, vault_service, cred_service = unlocked_setup
    sm = SessionManager(grace_seconds=15, countdown_seconds=120)

    view = UnlockedView(
        vault=vault,
        login_id="alice",
        vault_service=vault_service,
        credential_service=cred_service,
        session_manager=sm,
    )
    view.show()
    sm.start_session()
    sm._on_grace_timeout()
    assert view.countdown_label.isVisible() is True

    # Type into search input
    key_event = QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_G, Qt.KeyboardModifier.NoModifier, "g")
    sm._filter.eventFilter(view.search_input, key_event)

    assert view.countdown_label.isVisible() is False
    assert sm.state == SessionInactivityState.GRACE_PERIOD
    sm.stop_session()


def test_credential_list_scrolling_resets_inactivity(qapp: QApplication, unlocked_setup) -> None:
    """23. Credential list scrolling resets inactivity."""
    vault, vault_service, cred_service = unlocked_setup
    sm = SessionManager(grace_seconds=15, countdown_seconds=120)

    view = UnlockedView(
        vault=vault,
        login_id="alice",
        vault_service=vault_service,
        credential_service=cred_service,
        session_manager=sm,
    )
    view.show()
    sm.start_session()
    sm._on_grace_timeout()
    assert view.countdown_label.isVisible() is True

    # Scroll event on list
    wheel_event = QWheelEvent(
        QPointF(50.0, 50.0),
        QPointF(50.0, 50.0),
        QPoint(0, 120),
        QPoint(0, 120),
        Qt.MouseButton.NoButton,
        Qt.KeyboardModifier.NoModifier,
        Qt.ScrollPhase.NoScrollPhase,
        False,
    )
    sm._filter.eventFilter(view.credential_list, wheel_event)

    assert view.countdown_label.isVisible() is False
    assert sm.state == SessionInactivityState.GRACE_PERIOD
    sm.stop_session()


def test_view_edit_delete_interaction_resets_inactivity(qapp: QApplication, unlocked_setup) -> None:
    """24. View/Edit/Delete interaction resets inactivity."""
    vault, vault_service, cred_service = unlocked_setup
    sm = SessionManager(grace_seconds=15, countdown_seconds=120)

    view = UnlockedView(
        vault=vault,
        login_id="alice",
        vault_service=vault_service,
        credential_service=cred_service,
        session_manager=sm,
    )
    view.show()
    sm.start_session()
    sm._on_grace_timeout()
    assert sm.state == SessionInactivityState.COUNTDOWN

    # Click event on add button or any card button
    click_event = QMouseEvent(
        QEvent.Type.MouseButtonPress,
        QPointF(5.0, 5.0),
        QPointF(5.0, 5.0),
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    sm._filter.eventFilter(view.add_btn, click_event)

    assert sm.state == SessionInactivityState.GRACE_PERIOD
    assert view.countdown_label.isVisible() is False
    sm.stop_session()


# =========================================================================
# 6. Security & Edge Case Tests
# =========================================================================

def test_no_sensitive_data_stored_in_session_manager() -> None:
    """25. No sensitive data is stored inside the session timer/controller."""
    sm = SessionManager(grace_seconds=15, countdown_seconds=120)

    prohibited_substrings = [
        "password",
        "master",
        "kek",
        "dek",
        "secret",
        "credential",
        "key",
    ]

    for attr_name in dir(sm):
        lower_name = attr_name.lower()
        for forbidden in prohibited_substrings:
            # Must not have attributes named like secret keys or passwords
            assert forbidden not in lower_name, f"Forbidden attribute found on SessionManager: {attr_name}"

    # Also check filter
    for attr_name in dir(sm._filter):
        lower_name = attr_name.lower()
        for forbidden in prohibited_substrings:
            assert forbidden not in lower_name, f"Forbidden attribute found on ActivityEventFilter: {attr_name}"


def test_edge_case_rapid_multiple_interactions(qapp: QApplication) -> None:
    """26. Rapid repeated interactions reset grace timer without errors or leaks."""
    sm = SessionManager(grace_seconds=15, countdown_seconds=120)
    sm.start_session()

    for _ in range(50):
        sm.reset_activity()

    assert sm.state == SessionInactivityState.GRACE_PERIOD
    assert sm.is_countdown_visible is False
    assert sm.remaining_seconds == 120
    sm.stop_session()


def test_edge_case_dialog_closed_on_auto_lock(qapp: QApplication, unlocked_setup) -> None:
    """27. Any open modal dialog is rejected/closed when auto-lock occurs."""
    vault, vault_service, cred_service = unlocked_setup
    sm = SessionManager(grace_seconds=15, countdown_seconds=1)

    view = UnlockedView(
        vault=vault,
        login_id="alice",
        vault_service=vault_service,
        credential_service=cred_service,
        session_manager=sm,
    )
    sm.start_session()
    sm._on_grace_timeout()

    # Create dummy child dialog
    dlg = QDialog(view)
    dlg.show()
    assert dlg.isVisible() is True

    # Trigger auto-lock
    sm._on_countdown_tick()

    assert dlg.isVisible() is False
    assert vault.is_locked is True


def test_format_time_utility() -> None:
    """Verify time formatting MM:SS."""
    assert SessionManager.format_time(120) == "Auto-lock: 02:00"
    assert SessionManager.format_time(119) == "Auto-lock: 01:59"
    assert SessionManager.format_time(60) == "Auto-lock: 01:00"
    assert SessionManager.format_time(59) == "Auto-lock: 00:59"
    assert SessionManager.format_time(1) == "Auto-lock: 00:01"
    assert SessionManager.format_time(0) == "Auto-lock: 00:00"


def test_header_alignment_unaffected_by_countdown_visibility(qapp: QApplication, unlocked_setup) -> None:
    """Verify that the header remains centered regardless of timer visibility."""
    vault, vault_service, cred_service = unlocked_setup
    sm = SessionManager(grace_seconds=15, countdown_seconds=120)

    view = UnlockedView(
        vault=vault,
        login_id="alice",
        vault_service=vault_service,
        credential_service=cred_service,
        session_manager=sm,
    )
    view.show()
    qapp.processEvents()

    header = None
    for label in view.findChildren(QLabel):
        if "SecureVault — Unlocked" in label.text():
            header = label
            break

    assert header is not None

    # State 1: Hidden during grace period
    sm.start_session()
    qapp.processEvents()
    assert view.countdown_label.isVisible() is False
    center_hidden = header.geometry().x() + header.geometry().width() / 2

    # State 2: Visible countdown
    sm._on_grace_timeout()
    qapp.processEvents()
    assert view.countdown_label.isVisible() is True
    center_visible = header.geometry().x() + header.geometry().width() / 2

    # State 3: Counting down
    sm._on_countdown_tick()
    qapp.processEvents()
    center_ticking = header.geometry().x() + header.geometry().width() / 2

    # State 4: Reset / hidden again after user activity
    sm.reset_activity()
    qapp.processEvents()
    assert view.countdown_label.isVisible() is False
    center_hidden_again = header.geometry().x() + header.geometry().width() / 2

    # Verify horizontal center is identical across all states
    assert center_hidden == center_visible == center_ticking == center_hidden_again
    assert center_hidden == view.width() / 2
    sm.stop_session()


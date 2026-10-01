"""Tests for Auto-Lock Configuration & Live SessionManager Updates (Milestone M8).

Verifies:
    1. Supported timeouts: 120, 300, 600, 900 seconds
    2. Invalid timeout rejection in SettingsService
    3. Persistence across SettingsService reloads
    4. Live SessionManager countdown update without restart
    5. Grace period remains strictly system-defined at 15 seconds
    6. M7 inactivity state machine behavior preserved with new timeouts
    7. Countdown adjustments during active countdown state
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest
from PySide6.QtWidgets import QApplication

os.environ["QT_QPA_PLATFORM"] = "offscreen"


@pytest.fixture(scope="session")
def qapp() -> QApplication:
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    return app


from app.core.config import ACTIVITY_GRACE_SECONDS, AppConfig
from app.core.exceptions import ConfigurationError
from app.services.session_manager import SessionInactivityState, SessionManager
from app.services.settings_service import (
    SUPPORTED_AUTO_LOCK_TIMEOUTS,
    SettingsService,
)


@pytest.mark.parametrize("timeout", [120, 300, 600, 900])
def test_all_supported_timeouts_accepted_and_persisted(tmp_path: Path, timeout: int) -> None:
    """1. Verify 120, 300, 600, 900 seconds are accepted and persisted."""
    config = AppConfig(data_dir=tmp_path)
    service1 = SettingsService(config)

    service1.set_auto_lock_timeout(timeout)
    assert service1.get_settings().auto_lock_timeout == timeout

    service2 = SettingsService(config)
    assert service2.get_settings().auto_lock_timeout == timeout


@pytest.mark.parametrize("invalid_timeout", [0, -10, 60, 180, 1200, "fast"])
def test_invalid_timeouts_rejected_by_settings(tmp_path: Path, invalid_timeout: object) -> None:
    """2. Verify non-supported timeouts are rejected by SettingsService."""
    config = AppConfig(data_dir=tmp_path)
    service = SettingsService(config)

    with pytest.raises(ConfigurationError):
        service.set_auto_lock_timeout(invalid_timeout)  # type: ignore


def test_grace_period_remains_15_seconds() -> None:
    """3. Verify ACTIVITY_GRACE_SECONDS is strictly 15 and unconfigurable."""
    assert ACTIVITY_GRACE_SECONDS == 15

    sm = SessionManager()
    assert sm.grace_seconds == 15

    # Changing countdown seconds does not alter grace period
    sm.set_countdown_seconds(600)
    assert sm.grace_seconds == 15
    assert sm.countdown_seconds == 600


def test_live_session_manager_timeout_update_while_inactive() -> None:
    """4. Verify changing timeout while vault is inactive updates SessionManager."""
    sm = SessionManager(countdown_seconds=120)
    assert sm.countdown_seconds == 120
    assert sm.remaining_seconds == 120

    sm.set_countdown_seconds(300)
    assert sm.countdown_seconds == 300
    assert sm.remaining_seconds == 300


def test_live_session_manager_timeout_update_during_grace_period() -> None:
    """5. Verify changing timeout during grace period updates remaining countdown duration."""
    sm = SessionManager(countdown_seconds=120)
    sm.start_session()
    assert sm.state == SessionInactivityState.GRACE_PERIOD
    assert sm.remaining_seconds == 120

    sm.set_countdown_seconds(600)
    assert sm.countdown_seconds == 600
    assert sm.remaining_seconds == 600
    assert sm.state == SessionInactivityState.GRACE_PERIOD


def test_live_session_manager_timeout_update_during_countdown() -> None:
    """6. Verify changing timeout during countdown adjusts remaining seconds smoothly."""
    sm = SessionManager(countdown_seconds=120)
    sm.start_session()
    sm._on_grace_timeout()
    assert sm.state == SessionInactivityState.COUNTDOWN
    assert sm.remaining_seconds == 120

    # 10 ticks pass
    for _ in range(10):
        sm._on_countdown_tick()
    assert sm.remaining_seconds == 110

    # User changes timeout from 120s to 300s (diff +180s)
    sm.set_countdown_seconds(300)
    assert sm.countdown_seconds == 300
    assert sm.remaining_seconds == 290
    assert sm.state == SessionInactivityState.COUNTDOWN


def test_m7_state_machine_intact_with_new_timeout() -> None:
    """7. Verify full M7 state machine works correctly with updated timeout (300s)."""
    sm = SessionManager(grace_seconds=15, countdown_seconds=300)
    assert sm.countdown_seconds == 300

    # 1. Start session
    sm.start_session()
    assert sm.state == SessionInactivityState.GRACE_PERIOD
    assert sm.is_countdown_visible is False

    # 2. Activity in grace period resets
    sm.reset_activity()
    assert sm.state == SessionInactivityState.GRACE_PERIOD
    assert sm.is_countdown_visible is False

    # 3. Grace expiration enters countdown at 05:00
    sm._on_grace_timeout()
    assert sm.state == SessionInactivityState.COUNTDOWN
    assert sm.is_countdown_visible is True
    assert sm.remaining_seconds == 300
    assert sm.format_time(sm.remaining_seconds) == "Auto-lock: 05:00"

    # 4. Activity in countdown resets to grace period and hides countdown
    sm.reset_activity()
    assert sm.state == SessionInactivityState.GRACE_PERIOD
    assert sm.is_countdown_visible is False

    # 5. Enter countdown again and tick to 0
    sm._on_grace_timeout()
    assert sm.state == SessionInactivityState.COUNTDOWN

    # Simulate reaching timeout
    sm._remaining_seconds = 1
    locked_signals = []
    sm.timeout_triggered.connect(lambda: locked_signals.append(True))

    sm._on_countdown_tick()
    assert sm.state == SessionInactivityState.LOCKED
    assert sm.remaining_seconds == 0
    assert len(locked_signals) == 1

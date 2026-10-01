"""SecureVault — Session Management & Inactivity Watchdog (Milestone M7).

Orchestrates session inactivity tracking, grace period, visible countdown,
and automatic locking:
  1. Active Interaction (typing, clicking, scrolling) -> Inactivity timer resets, countdown hidden.
  2. 15-second grace period -> Inactivity countdown completely hidden.
  3. 2-minute visible countdown -> Appears in top-right corner, starts at 02:00, decrements once per second.
  4. Automatic Lock -> When reaching 00:00, automatically triggers existing lock sequence.

CRITICAL SECURITY BOUNDARY:
Under NO circumstances does SessionManager hold, store, or log:
  - Master password
  - Key Encryption Keys (KEK)
  - Data Encryption Keys (DEK)
  - Credential plaintexts or passwords
SessionManager stores strictly non-sensitive timing and session state flags.
"""

from __future__ import annotations

from enum import Enum
from typing import Callable

from PySide6.QtCore import QEvent, QObject, QTimer, Signal
from PySide6.QtWidgets import QApplication

from app.core.config import ACTIVITY_GRACE_SECONDS, INACTIVITY_TIMEOUT_SECONDS
from app.core.logging import get_logger

logger = get_logger("services.session_manager")


class SessionInactivityState(str, Enum):
    """Lifecycle states of the session inactivity watchdog."""

    INACTIVE = "INACTIVE"
    GRACE_PERIOD = "GRACE_PERIOD"
    COUNTDOWN = "COUNTDOWN"
    LOCKED = "LOCKED"


class ActivityEventFilter(QObject):
    """Event filter intercepting user interactions (typing, clicking, scrolling).

    Explicitly excludes mouse movement to prevent accidental session extension.
    """

    def __init__(self, on_activity: Callable[[], None], parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._on_activity = on_activity
        self._enabled = False
        self._target: QObject | None = None
        self.destroyed.connect(self.uninstall)

    def set_enabled(self, enabled: bool) -> None:
        """Enable or disable activity interception."""
        self._enabled = enabled

    def is_enabled(self) -> bool:
        """Return whether activity interception is currently enabled."""
        return self._enabled

    def install(self, target: QObject) -> None:
        """Install filter on target QObject."""
        if self._target is not None:
            self.uninstall()
        target.installEventFilter(self)
        self._target = target
        self._enabled = True

    def uninstall(self) -> None:
        """Safely remove filter from target QObject."""
        self._enabled = False
        if self._target is not None:
            try:
                self._target.removeEventFilter(self)
            except (RuntimeError, TypeError):
                pass
            self._target = None

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        """Filter events to detect user typing, clicking, or scrolling."""
        if self._enabled:
            event_type = event.type()
            # Explicitly only typing (KeyPress), clicking (MouseButtonPress), and scrolling (Wheel)
            if event_type in (
                QEvent.Type.KeyPress,
                QEvent.Type.MouseButtonPress,
                QEvent.Type.Wheel,
            ):
                self._on_activity()
        return super().eventFilter(watched, event)


class SessionManager(QObject):
    """Manages session inactivity timing, countdown display, and auto-lock dispatch."""

    # Signals
    countdown_updated = Signal(int, str)  # remaining_seconds, formatted_str ("Auto-lock: MM:SS")
    countdown_visibility_changed = Signal(bool)  # True = visible, False = hidden
    timeout_triggered = Signal()  # Emitted when countdown reaches 00:00
    activity_detected = Signal()  # Emitted when user interaction resets inactivity

    def __init__(
        self,
        grace_seconds: int = ACTIVITY_GRACE_SECONDS,
        countdown_seconds: int = INACTIVITY_TIMEOUT_SECONDS,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._grace_seconds = grace_seconds
        self._countdown_seconds = countdown_seconds

        self._state = SessionInactivityState.INACTIVE
        self._remaining_seconds = countdown_seconds
        self._filter_installed = False

        # Activity filter
        self._filter = ActivityEventFilter(on_activity=self.reset_activity, parent=self)

        # 15-second grace timer (single-shot)
        self._grace_timer = QTimer(self)
        self._grace_timer.setSingleShot(True)
        self._grace_timer.timeout.connect(self._on_grace_timeout)

        # 2-minute countdown timer (1-second tick)
        self._countdown_timer = QTimer(self)
        self._countdown_timer.setInterval(1000)
        self._countdown_timer.timeout.connect(self._on_countdown_tick)

        # Cleanup filter when session manager is destroyed
        self.destroyed.connect(self.stop_session)

    @property
    def state(self) -> SessionInactivityState:
        """Return the current inactivity state."""
        return self._state

    @property
    def remaining_seconds(self) -> int:
        """Return the remaining countdown seconds."""
        return self._remaining_seconds

    @property
    def is_active(self) -> bool:
        """Return True if session inactivity monitoring is running."""
        return self._state in (
            SessionInactivityState.GRACE_PERIOD,
            SessionInactivityState.COUNTDOWN,
        )

    @property
    def is_countdown_visible(self) -> bool:
        """Return True if the countdown is currently visible."""
        return self._state == SessionInactivityState.COUNTDOWN

    @property
    def grace_seconds(self) -> int:
        """Return the grace period duration in seconds."""
        return self._grace_seconds

    @property
    def countdown_seconds(self) -> int:
        """Return the countdown duration in seconds."""
        return self._countdown_seconds

    def set_countdown_seconds(self, seconds: int) -> None:
        """Update countdown duration at runtime (e.g. 120, 300, 600, 900 seconds).

        Preserves the system-defined grace period (ACTIVITY_GRACE_SECONDS).
        If currently counting down, updates the remaining duration safely.
        """
        if not isinstance(seconds, int) or seconds <= 0:
            raise ValueError(
                f"Invalid auto-lock timeout: {seconds}. Must be a positive integer."
            )
        old_seconds = self._countdown_seconds
        self._countdown_seconds = seconds
        if self._state == SessionInactivityState.COUNTDOWN:
            diff = seconds - old_seconds
            self._remaining_seconds = max(1, self._remaining_seconds + diff)
            self.countdown_updated.emit(
                self._remaining_seconds,
                self.format_time(self._remaining_seconds),
            )
        elif self._state == SessionInactivityState.GRACE_PERIOD:
            self._remaining_seconds = seconds
            self.countdown_updated.emit(
                self._remaining_seconds,
                self.format_time(self._remaining_seconds),
            )
        else:
            self._remaining_seconds = seconds

    @staticmethod
    def format_time(seconds: int) -> str:
        """Format seconds into 'Auto-lock: MM:SS'."""
        mins = max(0, seconds) // 60
        secs = max(0, seconds) % 60
        return f"Auto-lock: {mins:02d}:{secs:02d}"

    def start_session(self) -> None:
        """Start the session inactivity monitoring workflow when the vault is unlocked."""
        if self._state in (SessionInactivityState.GRACE_PERIOD, SessionInactivityState.COUNTDOWN):
            self.reset_activity()
            return

        self._state = SessionInactivityState.GRACE_PERIOD
        self._remaining_seconds = self._countdown_seconds

        self._ensure_filter_installed()
        self._filter.set_enabled(True)

        self._grace_timer.stop()
        self._countdown_timer.stop()
        self._grace_timer.start(self._grace_seconds * 1000)

        self.countdown_visibility_changed.emit(False)
        self.countdown_updated.emit(
            self._remaining_seconds,
            self.format_time(self._remaining_seconds),
        )
        logger.info(
            "Session started: %ds grace period active, countdown hidden.",
            self._grace_seconds,
        )

    def reset_activity(self) -> None:
        """Reset the inactivity timer and hide countdown upon user interaction."""
        if self._state not in (
            SessionInactivityState.GRACE_PERIOD,
            SessionInactivityState.COUNTDOWN,
        ):
            return

        if self._state == SessionInactivityState.COUNTDOWN:
            self._countdown_timer.stop()
            self.countdown_visibility_changed.emit(False)

        self._state = SessionInactivityState.GRACE_PERIOD
        self._remaining_seconds = self._countdown_seconds

        self._grace_timer.stop()
        self._grace_timer.start(self._grace_seconds * 1000)

        self.countdown_visibility_changed.emit(False)
        self.countdown_updated.emit(
            self._remaining_seconds,
            self.format_time(self._remaining_seconds),
        )
        self.activity_detected.emit()

    def _on_grace_timeout(self) -> None:
        """Handle expiration of the 15-second grace period; show countdown at 02:00."""
        if self._state != SessionInactivityState.GRACE_PERIOD:
            return

        self._state = SessionInactivityState.COUNTDOWN
        self._remaining_seconds = self._countdown_seconds

        # Countdown becomes visible starting at 02:00 (or configured countdown_seconds)
        self.countdown_updated.emit(
            self._remaining_seconds,
            self.format_time(self._remaining_seconds),
        )
        self.countdown_visibility_changed.emit(True)

        self._countdown_timer.stop()
        self._countdown_timer.start(1000)
        logger.info(
            "Grace period expired. Countdown visible at %s.",
            self.format_time(self._remaining_seconds),
        )

    def _on_countdown_tick(self) -> None:
        """Tick once per second during countdown. Lock upon reaching 00:00."""
        if self._state != SessionInactivityState.COUNTDOWN:
            self._countdown_timer.stop()
            return

        self._remaining_seconds -= 1

        if self._remaining_seconds > 0:
            self.countdown_updated.emit(
                self._remaining_seconds,
                self.format_time(self._remaining_seconds),
            )
        else:
            self._remaining_seconds = 0
            self.countdown_updated.emit(0, self.format_time(0))
            self._countdown_timer.stop()
            self._state = SessionInactivityState.LOCKED
            self.countdown_visibility_changed.emit(False)
            self._filter.set_enabled(False)
            logger.info("Session inactivity reached 00:00. Triggering automatic lock.")
            self.timeout_triggered.emit()

    def stop_session(self) -> None:
        """Stop all timers, hide countdown, and disable activity monitoring."""
        self._grace_timer.stop()
        self._countdown_timer.stop()
        if self._state != SessionInactivityState.LOCKED:
            self._state = SessionInactivityState.INACTIVE
        self._remaining_seconds = self._countdown_seconds

        self._filter.uninstall()
        self._filter_installed = False

        self.countdown_visibility_changed.emit(False)
        self.countdown_updated.emit(
            self._remaining_seconds,
            self.format_time(self._remaining_seconds),
        )
        logger.info("Session stopped. All timers stopped and countdown hidden.")

    def _ensure_filter_installed(self) -> None:
        """Ensure the activity event filter is attached to QApplication."""
        app = QApplication.instance()
        if app is not None and not self._filter_installed:
            self._filter.install(app)
            self._filter_installed = True

    def install_event_filter(self, target: QObject) -> None:
        """Explicitly install the event filter on a specific QObject (useful for tests)."""
        self._filter.install(target)
        self._filter_installed = True

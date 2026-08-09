"""Idle Detection Service - Detects user inactivity periods.

Monitors keyboard and mouse activity to determine whether the user is
actively interacting with the desktop, separating active sessions from
inactive periods.
"""

import logging
import time
from datetime import datetime
from typing import Any, Optional

from PySide6.QtCore import QObject, QTimer

from src.utils.signals import get_signals, BehavioralEvent
from src.utils.constants import IDLE_THRESHOLD_SECONDS

logger = logging.getLogger(__name__)


class IdleDetectionService(QObject):
    """Detects user idle periods based on input activity."""

    def __init__(self) -> None:
        super().__init__()
        self._signals = get_signals()
        self._active = False
        self._last_activity_time: float = time.time()
        self._idle_threshold = IDLE_THRESHOLD_SECONDS
        self._is_idle = False
        self._idle_start_time: Optional[float] = None
        self._total_idle_time = 0.0
        self._idle_periods: list[float] = []

        # Check timer
        self._timer = QTimer(self)
        self._timer.setInterval(5000)  # check every 5 seconds
        self._timer.timeout.connect(self._check_idle)

    def start(self) -> None:
        """Start idle detection."""
        self._active = True
        self._last_activity_time = time.time()
        self._timer.start()
        logger.info("Idle detection started")

    def stop(self) -> None:
        """Stop idle detection."""
        self._active = False
        self._timer.stop()
        logger.info("Idle detection stopped")

    def record_activity(self) -> None:
        """Record user activity, resetting idle state."""
        now = time.time()
        if self._is_idle and self._idle_start_time:
            idle_duration = now - self._idle_start_time
            self._idle_periods.append(idle_duration)
            self._total_idle_time += idle_duration

        self._last_activity_time = now
        self._is_idle = False
        self._idle_start_time = None

    def _check_idle(self) -> None:
        """Check if user has been idle beyond the threshold."""
        if not self._active:
            return

        elapsed = time.time() - self._last_activity_time

        if elapsed > self._idle_threshold and not self._is_idle:
            self._is_idle = True
            self._idle_start_time = time.time()
            logger.debug(f"User idle detected ({elapsed:.0f}s)")

            event = BehavioralEvent(
                event_type="idle",
                timestamp=datetime.now(),
                data={"idle_duration": elapsed, "threshold": self._idle_threshold},
            )
            self._signals.idle_event.emit(event)

        elif elapsed <= self._idle_threshold and self._is_idle:
            # User became active again
            self.record_activity()
            event = BehavioralEvent(
                event_type="active",
                timestamp=datetime.now(),
                data={"idle_duration": 0},
            )
            self._signals.idle_event.emit(event)

    @property
    def is_idle(self) -> bool:
        return self._is_idle

    @property
    def idle_duration(self) -> float:
        """Get current idle duration in seconds."""
        if self._is_idle and self._idle_start_time:
            return time.time() - self._idle_start_time
        return 0.0

    def get_stats(self) -> dict[str, Any]:
        """Get idle detection statistics."""
        return {
            "active": self._active,
            "is_idle": self._is_idle,
            "current_idle_duration": self.idle_duration,
            "total_idle_time": self._total_idle_time,
            "idle_periods": len(self._idle_periods),
            "avg_idle_duration": (sum(self._idle_periods) / len(self._idle_periods)
                                  if self._idle_periods else 0.0),
            "threshold": self._idle_threshold,
        }

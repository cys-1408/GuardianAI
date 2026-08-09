"""Scroll Monitoring Service - Captures scrolling behavior characteristics."""

import logging
import time
from collections import deque
from datetime import datetime
from typing import Any, Optional

from src.utils.signals import get_signals, BehavioralEvent
from src.behavior.event_buffer import EventBuffer

logger = logging.getLogger(__name__)


class ScrollMonitoringService:
    """Captures scrolling behavioral characteristics."""

    def __init__(self, event_buffer: EventBuffer) -> None:
        self._buffer = event_buffer
        self._signals = get_signals()
        self._active = False
        self._scroll_events: deque[dict[str, Any]] = deque(maxlen=500)
        self._last_scroll_time: Optional[float] = None
        self._total_scroll_distance = 0.0
        self._direction_changes = 0
        self._last_direction: Optional[str] = None
        self._scroll_speeds: list[float] = []
        self._pause_durations: list[float] = []

    def start(self) -> None:
        """Start scroll monitoring."""
        self._active = True
        logger.info("Scroll monitoring started")

    def stop(self) -> None:
        """Stop scroll monitoring."""
        self._active = False
        logger.info("Scroll monitoring stopped")

    def on_scroll(self, delta: int, direction: str = "down",
                  session_id: Optional[str] = None) -> None:
        """Handle a scroll event.

        Args:
            delta: Scroll amount
            direction: 'up' or 'down'
            session_id: Current session ID
        """
        if not self._active:
            return

        now = time.time()
        speed = abs(delta) / max(now - (self._last_scroll_time or now), 0.001)

        # Detect direction changes
        if self._last_direction and self._last_direction != direction:
            self._direction_changes += 1
            self._pause_durations.append(now - (self._last_scroll_time or now))

        self._last_direction = direction
        self._last_scroll_time = now
        self._total_scroll_distance += abs(delta)
        self._scroll_speeds.append(speed)

        event = BehavioralEvent(
            event_type="scroll",
            timestamp=datetime.now(),
            data={
                "delta": delta,
                "direction": direction,
                "speed": speed,
                "total_distance": self._total_scroll_distance,
            },
            session_id=session_id,
        )
        self._buffer.push(event)
        self._scroll_events.append(event.data)

    def get_scroll_speed(self) -> float:
        """Get average scroll speed.

        Returns:
            Average scroll speed
        """
        if not self._scroll_speeds:
            return 0.0
        return sum(self._scroll_speeds) / len(self._scroll_speeds)

    def get_scroll_rhythm(self) -> float:
        """Get scroll rhythm consistency (lower = more consistent).

        Returns:
            Standard deviation of scroll intervals
        """
        if len(self._scroll_events) < 2:
            return 0.0
        times = [e.get("event_time", 0) for e in self._scroll_events]
        intervals = [times[i] - times[i-1] for i in range(1, len(times))]
        if not intervals:
            return 0.0
        mean = sum(intervals) / len(intervals)
        variance = sum((i - mean)**2 for i in intervals) / len(intervals)
        return math.sqrt(variance)

    def get_stats(self) -> dict[str, Any]:
        """Get scroll monitoring statistics."""
        return {
            "active": self._active,
            "total_events": len(self._scroll_events),
            "avg_speed": self.get_scroll_speed(),
            "direction_changes": self._direction_changes,
            "total_distance": self._total_scroll_distance,
            "avg_pause": (sum(self._pause_durations) / len(self._pause_durations)
                         if self._pause_durations else 0.0),
        }

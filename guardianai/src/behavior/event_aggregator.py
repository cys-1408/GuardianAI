"""Event Aggregator - Combines related behavioral events into interaction windows.

Groups keyboard, mouse, scrolling, and idle events into synchronized
behavioral windows based on configurable time intervals before feature extraction.
"""

import logging
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any, Optional

from src.utils.signals import BehavioralEvent, get_signals
from src.utils.constants import BEHAVIORAL_WINDOW_SECONDS

logger = logging.getLogger(__name__)


class BehavioralWindow:
    """A time-based window of aggregated behavioral events."""

    def __init__(self, start_time: datetime, window_seconds: int = 60) -> None:
        self.start_time = start_time
        self.end_time = start_time + timedelta(seconds=window_seconds)
        self.window_seconds = window_seconds
        self.keyboard_events: list[BehavioralEvent] = []
        self.mouse_events: list[BehavioralEvent] = []
        self.scroll_events: list[BehavioralEvent] = []
        self.idle_events: list[BehavioralEvent] = []
        self.session_id: Optional[str] = None

    def add_event(self, event: BehavioralEvent) -> None:
        """Add an event to the appropriate category."""
        if event.event_type in ("key_press", "key_release"):
            self.keyboard_events.append(event)
        elif event.event_type in ("mouse_move", "mouse_click", "mouse_drag"):
            self.mouse_events.append(event)
        elif event.event_type == "scroll":
            self.scroll_events.append(event)
        elif event.event_type == "idle":
            self.idle_events.append(event)

        if not self.session_id and event.session_id:
            self.session_id = event.session_id

    @property
    def is_complete(self) -> bool:
        """Check if the window's time period has elapsed."""
        return datetime.now() >= self.end_time

    @property
    def duration(self) -> float:
        """Get the actual duration of events in this window."""
        if self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return 0.0

    @property
    def event_count(self) -> int:
        """Get total event count in this window."""
        return (len(self.keyboard_events) + len(self.mouse_events) +
                len(self.scroll_events) + len(self.idle_events))

    def get_summary(self) -> dict[str, Any]:
        """Get a summary of events in this window."""
        return {
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat(),
            "duration": self.duration,
            "keyboard_count": len(self.keyboard_events),
            "mouse_count": len(self.mouse_events),
            "scroll_count": len(self.scroll_events),
            "idle_count": len(self.idle_events),
            "total_events": self.event_count,
            "session_id": self.session_id,
        }


class EventAggregator:
    """Aggregates behavioral events into time-based behavioral windows."""

    def __init__(self, window_seconds: int = BEHAVIORAL_WINDOW_SECONDS) -> None:
        self._window_seconds = window_seconds
        self._current_window: Optional[BehavioralWindow] = None
        self._completed_windows: list[BehavioralWindow] = []
        self._signals = get_signals()
        self._total_windows_created = 0

    def add_event(self, event: BehavioralEvent) -> Optional[BehavioralWindow]:
        """Add an event and return completed windows if any.

        Args:
            event: Behavioral event to add

        Returns:
            Completed behavioral window if one was finalized, None otherwise
        """
        if (self._current_window is None or
                event.timestamp > self._current_window.end_time):
            # Start a new window
            completed = self._current_window
            self._current_window = BehavioralWindow(
                event.timestamp, self._window_seconds
            )
            self._total_windows_created += 1

            if completed and completed.event_count > 0:
                self._completed_windows.append(completed)
                return completed

        self._current_window.add_event(event)
        return None

    def get_completed_windows(self) -> list[BehavioralWindow]:
        """Get and clear completed behavioral windows.

        Returns:
            List of completed windows
        """
        windows = list(self._completed_windows)
        self._completed_windows.clear()
        return windows

    def force_window_completion(self) -> Optional[BehavioralWindow]:
        """Force the current window to complete.

        Returns:
            The completed window or None
        """
        if self._current_window and self._current_window.event_count > 0:
            window = self._current_window
            self._current_window = None
            return window
        return None

    def get_stats(self) -> dict[str, Any]:
        """Get aggregation statistics."""
        pending_windows = len(self._completed_windows)
        if self._current_window:
            pending_windows += 1
        return {
            "total_windows_created": self._total_windows_created,
            "pending_windows": pending_windows,
            "window_seconds": self._window_seconds,
            "current_window_events": self._current_window.event_count if self._current_window else 0,
        }

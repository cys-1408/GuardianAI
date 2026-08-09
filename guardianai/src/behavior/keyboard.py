"""Keyboard Monitoring Service - Captures keyboard interaction events.

Monitors keyboard events in the background without recording actual typed
content, extracting only timing characteristics for behavioral analysis.
"""

import logging
import time
from collections import defaultdict
from datetime import datetime
from typing import Any, Optional

from src.utils.signals import get_signals, BehavioralEvent
from src.behavior.event_buffer import EventBuffer

logger = logging.getLogger(__name__)


class KeyboardMonitoringService:
    """Captures keyboard behavioral characteristics."""

    def __init__(self, event_buffer: EventBuffer) -> None:
        self._buffer = event_buffer
        self._signals = get_signals()
        self._active = False
        self._pressed_keys: dict[int, float] = {}  # key_code -> press_time
        self._keystroke_times: list[float] = []
        self._last_release_time: Optional[float] = None
        self._error_key_codes = {8, 46}  # Backspace, Delete

    def start(self) -> None:
        """Start keyboard monitoring."""
        self._active = True
        self._pressed_keys.clear()
        self._keystroke_times.clear()
        logger.info("Keyboard monitoring started")

    def stop(self) -> None:
        """Stop keyboard monitoring."""
        self._active = False
        logger.info("Keyboard monitoring stopped")

    def on_key_press(self, key_code: int, session_id: Optional[str] = None) -> None:
        """Handle a key press event.

        Args:
            key_code: Virtual key code
            session_id: Current session ID
        """
        if not self._active:
            return

        press_time = time.time()
        self._pressed_keys[key_code] = press_time
        self._keystroke_times.append(press_time)

        # Calculate flight time (time since last key release)
        flight_time = 0.0
        if self._last_release_time is not None:
            flight_time = press_time - self._last_release_time

        event = BehavioralEvent(
            event_type="key_press",
            timestamp=datetime.now(),
            data={
                "key_code": key_code,
                "press_time": press_time,
                "flight_time": flight_time,
                "is_error": key_code in self._error_key_codes,
            },
            session_id=session_id,
        )
        self._buffer.push(event)

    def on_key_release(self, key_code: int, session_id: Optional[str] = None) -> None:
        """Handle a key release event.

        Args:
            key_code: Virtual key code
            session_id: Current session ID
        """
        if not self._active:
            return

        release_time = time.time()
        self._last_release_time = release_time

        # Calculate dwell time (time between press and release)
        dwell_time = 0.0
        if key_code in self._pressed_keys:
            dwell_time = release_time - self._pressed_keys[key_code]
            del self._pressed_keys[key_code]

        event = BehavioralEvent(
            event_type="key_release",
            timestamp=datetime.now(),
            data={
                "key_code": key_code,
                "release_time": release_time,
                "dwell_time": dwell_time,
            },
            session_id=session_id,
        )
        self._buffer.push(event)

    def get_typing_speed(self, window_seconds: float = 60.0) -> float:
        """Calculate typing speed in keys per minute.

        Args:
            window_seconds: Time window for calculation

        Returns:
            Typing speed (keys/minute)
        """
        if not self._keystroke_times:
            return 0.0

        now = time.time()
        cutoff = now - window_seconds
        recent = [t for t in self._keystroke_times if t > cutoff]

        if not recent:
            return 0.0

        actual_window = min(now - min(recent), window_seconds)
        if actual_window <= 0:
            return 0.0

        return (len(recent) / actual_window) * 60.0

    def get_stats(self) -> dict[str, Any]:
        """Get keyboard monitoring statistics."""
        return {
            "active": self._active,
            "pressed_keys_count": len(self._pressed_keys),
            "total_keystrokes": len(self._keystroke_times),
            "typing_speed_cpm": self.get_typing_speed(),
        }

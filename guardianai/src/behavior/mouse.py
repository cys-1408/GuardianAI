"""Mouse Monitoring Service - Captures mouse interaction characteristics."""

import logging
import math
import time
from collections import deque
from datetime import datetime
from typing import Any, Optional

from src.utils.signals import get_signals, BehavioralEvent
from src.behavior.event_buffer import EventBuffer

logger = logging.getLogger(__name__)


class MouseMonitoringService:
    """Captures mouse behavioral characteristics."""

    def __init__(self, event_buffer: EventBuffer) -> None:
        self._buffer = event_buffer
        self._signals = get_signals()
        self._active = False
        self._last_x: Optional[float] = None
        self._last_y: Optional[float] = None
        self._last_move_time: Optional[float] = None
        self._positions: deque[tuple[float, float, float]] = deque(maxlen=1000)  # (x, y, time)
        self._click_times: list[float] = []
        self._click_positions: list[tuple[float, float]] = []
        self._drag_active = False
        self._drag_start: Optional[tuple[float, float, float]] = None
        self._click_counts: dict[str, int] = {"left": 0, "right": 0, "middle": 0}
        self._double_clicks = 0

    def start(self) -> None:
        """Start mouse monitoring."""
        self._active = True
        logger.info("Mouse monitoring started")

    def stop(self) -> None:
        """Stop mouse monitoring."""
        self._active = False
        logger.info("Mouse monitoring stopped")

    def on_mouse_move(self, x: float, y: float, session_id: Optional[str] = None) -> None:
        """Handle a mouse movement event.

        Args:
            x: Current X position
            y: Current Y position
            session_id: Current session ID
        """
        if not self._active:
            return

        now = time.time()
        velocity = 0.0
        acceleration = 0.0
        angle = 0.0

        if self._last_x is not None and self._last_y is not None:
            dx = x - self._last_x
            dy = y - self._last_y
            dt = now - (self._last_move_time or now)

            if dt > 0:
                velocity = math.sqrt(dx*dx + dy*dy) / dt
                # Calculate angle of movement (radians)
                if dx != 0 or dy != 0:
                    angle = math.atan2(dy, dx)

                # Calculate acceleration
                if len(self._positions) >= 2:
                    prev = self._positions[-1]
                    prev_velocity = math.sqrt(
                        (prev[0] - self._positions[-2][0])**2 +
                        (prev[1] - self._positions[-2][1])**2
                    ) / max(now - prev[2], 0.001)
                    acceleration = velocity - prev_velocity

            self._positions.append((x, y, now))

        self._last_x = x
        self._last_y = y
        self._last_move_time = now

        event = BehavioralEvent(
            event_type="mouse_move",
            timestamp=datetime.now(),
            data={
                "x": x, "y": y,
                "velocity": velocity,
                "acceleration": acceleration,
                "angle": angle,
            },
            session_id=session_id,
        )
        self._buffer.push(event)

    def on_mouse_click(self, x: float, y: float, button: str,
                       session_id: Optional[str] = None) -> None:
        """Handle a mouse click event.

        Args:
            x: Click X position
            y: Click Y position
            button: Mouse button ('left', 'right', 'middle')
            session_id: Current session ID
        """
        if not self._active:
            return

        now = time.time()
        self._click_times.append(now)
        self._click_positions.append((x, y))
        self._click_counts[button] = self._click_counts.get(button, 0) + 1

        # Detect double-click
        if len(self._click_times) >= 2:
            interval = now - self._click_times[-2]
            if interval < 0.5:  # 500ms double-click threshold
                self._double_clicks += 1

        # Check drag start
        if button == "left":
            self._drag_active = True
            self._drag_start = (x, y, now)

        event = BehavioralEvent(
            event_type="mouse_click",
            timestamp=datetime.now(),
            data={
                "x": x, "y": y,
                "button": button,
                "click_count": self._click_counts[button],
            },
            session_id=session_id,
        )
        self._buffer.push(event)

    def on_mouse_release(self, x: float, y: float, button: str,
                         session_id: Optional[str] = None) -> None:
        """Handle mouse button release.

        Args:
            x: Release X position
            y: Release Y position
            button: Mouse button
            session_id: Current session ID
        """
        if not self._active:
            return

        if button == "left" and self._drag_active and self._drag_start:
            now = time.time()
            drag_duration = now - self._drag_start[2]
            drag_distance = math.sqrt(
                (x - self._drag_start[0])**2 + (y - self._drag_start[1])**2
            )
            drag_speed = drag_distance / max(drag_duration, 0.001)

            event = BehavioralEvent(
                event_type="mouse_drag",
                timestamp=datetime.now(),
                data={
                    "start_x": self._drag_start[0],
                    "start_y": self._drag_start[1],
                    "end_x": x,
                    "end_y": y,
                    "distance": drag_distance,
                    "duration": drag_duration,
                    "speed": drag_speed,
                },
                session_id=session_id,
            )
            self._buffer.push(event)

        self._drag_active = False
        self._drag_start = None

    def get_stats(self) -> dict[str, Any]:
        """Get mouse monitoring statistics."""
        return {
            "active": self._active,
            "total_moves": len(self._positions),
            "total_clicks": len(self._click_times),
            "click_distribution": dict(self._click_counts),
            "double_clicks": self._double_clicks,
            "current_drag": self._drag_active,
        }

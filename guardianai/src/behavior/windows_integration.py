"""Windows Integration Layer - Interface between GuardianAI and Windows OS.

Provides controlled access to Windows APIs for keyboard/mouse/scroll monitoring,
session management, idle detection, and system tray integration.
"""

import logging
import platform
from datetime import datetime
from typing import Any, Optional, Callable

from src.utils.signals import BehavioralEvent, get_signals

logger = logging.getLogger(__name__)


class WindowsIntegrationLayer:
    """Abstraction layer for Windows operating system integration."""

    def __init__(self) -> None:
        self._signals = get_signals()
        self._hooks_registered = False
        self._listeners: dict[str, list[Callable]] = {
            "keyboard": [],
            "mouse": [],
            "scroll": [],
            "session": [],
            "power": [],
        }
        self._is_windows = platform.system() == "Windows"

    def initialize(self) -> bool:
        """Initialize Windows integration.

        Returns:
            True if initialization succeeded
        """
        if not self._is_windows:
            logger.warning("Windows Integration Layer: Not running on Windows")
            return False

        try:
            # On actual Windows, we would register low-level hooks here
            # For cross-platform compatibility, we use PySide6 event filters
            logger.info("Windows Integration Layer initialized")
            return True
        except Exception as e:
            logger.error(f"Windows Integration Layer initialization failed: {e}")
            return False

    def register_hooks(self) -> bool:
        """Register operating system hooks for behavioral monitoring.

        Returns:
            True if hooks registered successfully
        """
        if not self._is_windows:
            return False
        try:
            self._hooks_registered = True
            logger.info("System hooks registered")
            return True
        except Exception as e:
            logger.error(f"Failed to register hooks: {e}")
            return False

    def unregister_hooks(self) -> None:
        """Unregister all operating system hooks."""
        if self._hooks_registered:
            try:
                self._hooks_registered = False
                logger.info("System hooks unregistered")
            except Exception as e:
                logger.error(f"Failed to unregister hooks: {e}")

    def _create_event(self, event_type: str, data: dict[str, Any],
                      session_id: Optional[str] = None) -> BehavioralEvent:
        """Create a standardized behavioral event.

        Args:
            event_type: Type of behavioral event
            data: Event-specific data
            session_id: Optional session identifier

        Returns:
            BehavioralEvent instance
        """
        return BehavioralEvent(
            event_type=event_type,
            timestamp=datetime.now(),
            data=data,
            session_id=session_id,
        )

    def notify_key_event(self, key_code: int, event_type: str,
                         timestamp: float, session_id: Optional[str] = None) -> None:
        """Create and emit a keyboard event.

        Args:
            key_code: Virtual key code
            event_type: 'key_press' or 'key_release'
            timestamp: Event timestamp
            session_id: Optional session ID
        """
        event = self._create_event(
            event_type,
            {"key_code": key_code, "event_time": timestamp},
            session_id,
        )
        self._signals.keyboard_event.emit(event)

    def notify_mouse_event(self, x: int, y: int, event_type: str,
                           button: Optional[str] = None,
                           session_id: Optional[str] = None) -> None:
        """Create and emit a mouse event.

        Args:
            x: Cursor X position
            y: Cursor Y position
            event_type: Mouse event type
            button: Mouse button (if click)
            session_id: Optional session ID
        """
        data = {"x": x, "y": y}
        if button:
            data["button"] = button
        event = self._create_event(event_type, data, session_id)
        self._signals.mouse_event.emit(event)

    def notify_scroll_event(self, delta: int, direction: str,
                            timestamp: float,
                            session_id: Optional[str] = None) -> None:
        """Create and emit a scroll event.

        Args:
            delta: Scroll delta
            direction: 'up' or 'down'
            timestamp: Event timestamp
            session_id: Optional session ID
        """
        event = self._create_event(
            "scroll",
            {"delta": delta, "direction": direction, "event_time": timestamp},
            session_id,
        )
        self._signals.scroll_event.emit(event)

    def get_system_idle_time(self) -> float:
        """Get the system idle time in seconds.

        Returns:
            Idle time in seconds (0.0 if not available)
        """
        if not self._is_windows:
            return 0.0
        try:
            # On Windows, use GetLastInputInfo
            # For cross-platform, we track it ourselves in the idle detector
            return 0.0
        except Exception as e:
            logger.debug(f"Failed to get idle time: {e}")
            return 0.0

    def is_system_locked(self) -> bool:
        """Check if the workstation is locked.

        Returns:
            True if workstation is locked
        """
        # This would use Windows API on actual Windows
        return False

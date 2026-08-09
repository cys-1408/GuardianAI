"""Event Buffer - Temporarily stores behavioral events before processing.

Provides an in-memory queue with configurable capacity to prevent event
loss during high activity periods and maintain event ordering.
"""

import logging
import threading
from collections import deque
from datetime import datetime
from typing import Any, Optional

from src.utils.signals import BehavioralEvent, get_signals

logger = logging.getLogger(__name__)


class EventBuffer:
    """Thread-safe buffer for behavioral events with overflow protection."""

    def __init__(self, max_size: int = 10000) -> None:
        self._queue: deque[BehavioralEvent] = deque(maxlen=max_size)
        self._lock = threading.Lock()
        self._max_size = max_size
        self._dropped_count = 0
        self._total_received = 0

    @property
    def size(self) -> int:
        with self._lock:
            return len(self._queue)

    @property
    def dropped_count(self) -> int:
        return self._dropped_count

    def push(self, event: BehavioralEvent) -> bool:
        """Add an event to the buffer.

        Args:
            event: Behavioral event to buffer

        Returns:
            True if event was accepted
        """
        with self._lock:
            self._total_received += 1
            if len(self._queue) >= self._max_size:
                self._dropped_count += 1
                logger.warning(f"Event buffer full, dropping event: {event.event_type}")
                return False
            self._queue.append(event)
            return True

    def pop_batch(self, batch_size: int = 50) -> list[BehavioralEvent]:
        """Pop a batch of events from the buffer.

        Args:
            batch_size: Maximum number of events to pop

        Returns:
            List of buffered events
        """
        with self._lock:
            batch = []
            for _ in range(min(batch_size, len(self._queue))):
                batch.append(self._queue.popleft())
            return batch

    def pop_all(self) -> list[BehavioralEvent]:
        """Pop all events from the buffer."""
        with self._lock:
            events = list(self._queue)
            self._queue.clear()
            return events

    def flush(self) -> list[BehavioralEvent]:
        """Flush all buffered events."""
        return self.pop_all()

    def get_stats(self) -> dict[str, Any]:
        """Get buffer statistics."""
        with self._lock:
            return {
                "current_size": len(self._queue),
                "max_size": self._max_size,
                "dropped": self._dropped_count,
                "total_received": self._total_received,
                "usage_percent": (len(self._queue) / self._max_size) * 100,
            }

    def clear(self) -> None:
        """Clear all events from the buffer."""
        with self._lock:
            self._queue.clear()

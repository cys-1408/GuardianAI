"""Trust Score Manager - Maintains evolving trust scores for identity confidence."""

import logging
from collections import deque
from typing import Any, Optional

from src.utils.signals import get_signals
from src.utils.constants import (
    TRUST_WINDOW_SIZE, TRUST_HIGH_THRESHOLD,
    TRUST_MEDIUM_THRESHOLD, TRUST_LOW_THRESHOLD,
    TrustLevel,
)

logger = logging.getLogger(__name__)


class TrustScoreManager:
    """Manages dynamic trust scores for continuous authentication."""

    def __init__(self) -> None:
        self._signals = get_signals()
        self._current_trust: float = 0.7  # Start with moderate trust
        self._trust_history: deque[float] = deque(maxlen=TRUST_WINDOW_SIZE)
        self._session_trust: dict[str, float] = {}

    @property
    def current_trust(self) -> float:
        return self._current_trust

    def update(self, confidence: float, session_id: Optional[str] = None) -> float:
        """Update trust score based on authentication confidence.

        Args:
            confidence: Current authentication confidence
            session_id: Optional session identifier

        Returns:
            Updated trust score
        """
        # Weight recent confidence more heavily
        alpha = 0.3
        self._current_trust = (
            alpha * confidence + (1 - alpha) * self._current_trust
        )

        self._trust_history.append(self._current_trust)

        if session_id:
            self._session_trust[session_id] = self._current_trust

        self._signals.trust_updated.emit(self._current_trust)
        return self._current_trust

    def get_trust_level(self) -> TrustLevel:
        """Get the categorical trust level.

        Returns:
            High, Medium, or Low trust level
        """
        if self._current_trust >= TRUST_HIGH_THRESHOLD:
            return TrustLevel.HIGH
        elif self._current_trust >= TRUST_MEDIUM_THRESHOLD:
            return TrustLevel.MEDIUM
        return TrustLevel.LOW

    def is_trusted(self) -> bool:
        """Check if current trust is high enough for adaptive learning.

        Returns:
            True if trust is HIGH level
        """
        return self.get_trust_level() == TrustLevel.HIGH

    def detect_degradation(self, window: int = 10) -> bool:
        """Detect if trust is degrading significantly.

        Args:
            window: Number of recent values to check

        Returns:
            True if degradation detected
        """
        if len(self._trust_history) < window:
            return False
        recent = list(self._trust_history)[-window:]
        return (recent[-1] - recent[0]) < -0.2  # 20% drop

    def reset(self, initial: float = 0.7) -> None:
        """Reset trust to initial value."""
        self._current_trust = initial
        self._trust_history.clear()

    def get_stats(self) -> dict[str, Any]:
        """Get trust score statistics."""
        return {
            "current_trust": self._current_trust,
            "trust_level": self.get_trust_level().value,
            "history_length": len(self._trust_history),
            "is_degrading": self.detect_degradation(),
            "is_trusted": self.is_trusted(),
        }

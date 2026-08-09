"""Confidence Engine - Converts model predictions into standardized confidence values."""

import logging
from typing import Any

from src.utils.signals import get_signals
from src.utils.constants import CONFIDENCE_ALPHA

logger = logging.getLogger(__name__)


class ConfidenceEngine:
    """Calculates and smooths authentication confidence scores."""

    def __init__(self) -> None:
        self._signals = get_signals()
        self._current_confidence: float = 0.5
        self._alpha = CONFIDENCE_ALPHA
        self._confidence_history: list[float] = []
        self._max_history = 100

    @property
    def current_confidence(self) -> float:
        return self._current_confidence

    def update(self, raw_score: float) -> float:
        """Update confidence with a new prediction score using EMA smoothing.

        Args:
            raw_score: Raw prediction score [0, 1]

        Returns:
            Smoothed confidence value
        """
        # Ensure score is in [0, 1]
        score = max(0.0, min(1.0, raw_score))

        # Exponential Moving Average
        self._current_confidence = (
            self._alpha * score + (1 - self._alpha) * self._current_confidence
        )

        # Store history
        self._confidence_history.append(self._current_confidence)
        if len(self._confidence_history) > self._max_history:
            self._confidence_history.pop(0)

        self._signals.confidence_updated.emit(self._current_confidence)
        return self._current_confidence

    def reset(self, initial: float = 0.5) -> None:
        """Reset confidence to initial value.

        Args:
            initial: Initial confidence value
        """
        self._current_confidence = initial
        self._confidence_history.clear()

    def get_trend(self, window: int = 10) -> str:
        """Get the short-term confidence trend.

        Args:
            window: Number of recent values to analyze

        Returns:
            'increasing', 'decreasing', or 'stable'
        """
        if len(self._confidence_history) < window:
            return "stable"

        recent = self._confidence_history[-window:]
        if len(recent) < 2:
            return "stable"

        slope = (recent[-1] - recent[0]) / len(recent)
        if slope > 0.02:
            return "increasing"
        elif slope < -0.02:
            return "decreasing"
        return "stable"

    def get_stats(self) -> dict[str, Any]:
        """Get confidence engine statistics."""
        return {
            "current_confidence": self._current_confidence,
            "history_length": len(self._confidence_history),
            "smoothing_alpha": self._alpha,
            "trend": self.get_trend(),
            "min_conf": min(self._confidence_history) if self._confidence_history else 0.0,
            "max_conf": max(self._confidence_history) if self._confidence_history else 0.0,
        }

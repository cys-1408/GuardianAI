"""Adaptive Risk Engine - Continuously estimates authentication risk based on behavioral changes.

Analyzes behavioral deviation magnitude, confidence trends, and historical
consistency to estimate current authentication risk (Low/Medium/High/Critical).
"""

import logging
from typing import Any, Optional

import numpy as np

from src.utils.signals import get_signals
from src.utils.constants import (
    RISK_LOW, RISK_MEDIUM, RISK_HIGH, RISK_CRITICAL, RiskLevel,
)
from src.ai.confidence import ConfidenceEngine
from src.ai.trust import TrustScoreManager

logger = logging.getLogger(__name__)


class AdaptiveRiskEngine:
    """Estimates authentication risk from behavioral deviations and trends."""

    def __init__(self, trust_mgr: TrustScoreManager,
                 confidence_engine: ConfidenceEngine) -> None:
        self._trust = trust_mgr
        self._confidence = confidence_engine
        self._signals = get_signals()
        self._current_risk_level: str = RiskLevel.LOW.value
        self._risk_history: list[float] = []
        self._consecutive_low_confidence = 0
        self._max_history = 100

    @property
    def current_risk_level(self) -> str:
        return self._current_risk_level

    @property
    def current_risk_score(self) -> float:
        """Get current risk as a numeric score [0, 1]."""
        mapping = {
            RiskLevel.LOW.value: 0.0,
            RiskLevel.MEDIUM.value: 0.3,
            RiskLevel.HIGH.value: 0.6,
            RiskLevel.CRITICAL.value: 0.9,
        }
        return mapping.get(self._current_risk_level, 0.0)

    def evaluate(self, feature_vector: Optional[list[float]] = None) -> str:
        """Evaluate current risk level based on trust, confidence, and trends.

        Args:
            feature_vector: Optional feature vector for anomaly scoring

        Returns:
            Current risk level string
        """
        trust = self._trust.current_trust
        confidence = self._confidence.current_confidence
        trend = self._confidence.get_trend()
        trust_degrading = self._trust.detect_degradation()

        # Calculate anomaly score if features provided
        anomaly_score = self._compute_anomaly_score(feature_vector) if feature_vector else 0.0

        # Critical risk: very low trust or confidence, or high anomaly
        if trust < 0.2 or confidence < 0.15 or anomaly_score > 0.8:
            self._current_risk_level = RiskLevel.CRITICAL.value
        # High risk: degrading trust, low confidence, or elevated anomaly
        elif trust < 0.4 or confidence < 0.3 or trust_degrading or anomaly_score > 0.5:
            self._current_risk_level = RiskLevel.HIGH.value
        # Medium risk: moderate values or some anomaly
        elif trust < 0.6 or confidence < 0.5 or anomaly_score > 0.3:
            self._current_risk_level = RiskLevel.MEDIUM.value
        # Low risk: everything looks good
        else:
            self._current_risk_level = RiskLevel.LOW.value

        # Track consecutive low confidence
        if confidence < 0.4:
            self._consecutive_low_confidence += 1
            if self._consecutive_low_confidence >= 5:
                self._current_risk_level = RiskLevel.HIGH.value
        else:
            self._consecutive_low_confidence = 0

        # Store risk score history
        self._risk_history.append(self.current_risk_score)
        if len(self._risk_history) > self._max_history:
            self._risk_history.pop(0)

        self._signals.risk_updated.emit(self._current_risk_level)
        return self._current_risk_level

    def _compute_anomaly_score(self, feature_vector: list[float]) -> float:
        """Calculate anomaly score for a feature vector.

        Args:
            feature_vector: Normalized behavioral features

        Returns:
            Anomaly score [0, 1] where higher = more anomalous
        """
        if not feature_vector:
            return 0.0

        arr = np.array(feature_vector, dtype=np.float64)
        if np.std(arr) == 0:
            return 0.0

        z_scores = np.abs((arr - np.mean(arr)) / np.std(arr))
        anomaly_score = float(np.mean(z_scores >= 2.0))
        return min(1.0, anomaly_score)

    def get_stats(self) -> dict[str, Any]:
        """Get risk engine statistics."""
        return {
            "current_risk_level": self._current_risk_level,
            "risk_score": self.current_risk_score,
            "consecutive_low_confidence": self._consecutive_low_confidence,
            "history_length": len(self._risk_history),
        }

    def reset(self) -> None:
        """Reset risk assessment state."""
        self._current_risk_level = RiskLevel.LOW.value
        self._risk_history.clear()
        self._consecutive_low_confidence = 0

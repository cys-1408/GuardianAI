"""Tests for TrustScoreManager and AdaptiveRiskEngine."""

import pytest
from src.ai.trust import TrustScoreManager
from src.ai.risk import AdaptiveRiskEngine
from src.ai.confidence import ConfidenceEngine
from src.utils.constants import TrustLevel, RiskLevel


class TestTrustScoreManager:
    def setup_method(self):
        self.trust = TrustScoreManager()

    def test_initial_trust(self):
        assert self.trust.current_trust == 0.7

    def test_update_high_confidence(self):
        self.trust.update(0.95)
        assert self.trust.current_trust > 0.7

    def test_update_low_confidence(self):
        self.trust.update(0.1)
        assert self.trust.current_trust < 0.7

    def test_trust_level_high(self):
        self.trust.reset(0.9)
        assert self.trust.get_trust_level() == TrustLevel.HIGH

    def test_trust_level_medium(self):
        self.trust.reset(0.6)
        assert self.trust.get_trust_level() == TrustLevel.MEDIUM

    def test_trust_level_low(self):
        self.trust.reset(0.2)
        assert self.trust.get_trust_level() == TrustLevel.LOW

    def test_is_trusted(self):
        self.trust.reset(0.9)
        assert self.trust.is_trusted() == True

    def test_is_not_trusted(self):
        self.trust.reset(0.5)
        assert self.trust.is_trusted() == False

    def test_detect_degradation(self):
        self.trust.reset(0.9)
        for v in [0.85, 0.8, 0.75, 0.7, 0.65, 0.6, 0.55, 0.5, 0.45, 0.4]:
            self.trust.update(v)
        assert self.trust.detect_degradation() == True

    def test_reset(self):
        self.trust.update(0.3)
        self.trust.reset()
        assert self.trust.current_trust == 0.7


class TestAdaptiveRiskEngine:
    def setup_method(self):
        self.confidence = ConfidenceEngine()
        self.trust = TrustScoreManager()
        self.risk = AdaptiveRiskEngine(self.trust, self.confidence)

    def test_initial_risk_low(self):
        assert self.risk.current_risk_level == RiskLevel.LOW.value

    def test_risk_increases_with_low_trust(self):
        self.trust.reset(0.1)
        self.confidence.reset(0.9)
        level = self.risk.evaluate()
        assert level in [RiskLevel.CRITICAL.value, RiskLevel.HIGH.value]

    def test_risk_increases_with_low_confidence(self):
        self.trust.reset(0.9)
        self.confidence.reset(0.1)
        level = self.risk.evaluate()
        assert level in [RiskLevel.CRITICAL.value, RiskLevel.HIGH.value]

    def test_risk_low_with_good_values(self):
        self.trust.reset(0.9)
        self.confidence.reset(0.9)
        level = self.risk.evaluate()
        assert level == RiskLevel.LOW.value

    def test_anomaly_score(self):
        # Outlier (15.0) among uniform values gives z-score > 2.0
        score = self.risk._compute_anomaly_score([0.5, 0.5, 0.5, 0.5, 15.0])
        assert score > 0.0

    def test_anomaly_score_zero_for_normal(self):
        score = self.risk._compute_anomaly_score([0.5, 0.5, 0.5, 0.5, 0.5])
        assert score == 0.0

    def test_risk_stats(self):
        self.risk.evaluate()
        stats = self.risk.get_stats()
        assert "current_risk_level" in stats
        assert "risk_score" in stats

    def test_reset(self):
        self.trust.reset(0.1)
        self.risk.evaluate()
        self.risk.reset()
        assert self.risk.current_risk_level == RiskLevel.LOW.value

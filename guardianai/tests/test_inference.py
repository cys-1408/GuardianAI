"""Tests for Inference Engine and Confidence Engine."""

import pytest
import numpy as np
from sklearn.ensemble import IsolationForest
from src.ai.confidence import ConfidenceEngine
from src.ai.model_wrapper import EnsembleModelWrapper
from src.utils.constants import RANDOM_STATE


class TestConfidenceEngine:
    def setup_method(self):
        self.engine = ConfidenceEngine()

    def test_initial_confidence(self):
        assert self.engine.current_confidence == 0.5

    def test_update_increases_confidence(self):
        self.engine.update(0.9)
        assert self.engine.current_confidence > 0.5

    def test_update_decreases_confidence(self):
        self.engine.update(0.1)
        assert self.engine.current_confidence < 0.5

    def test_smoothing_behavior(self):
        self.engine.update(1.0)
        conf1 = self.engine.current_confidence
        self.engine.update(1.0)
        conf2 = self.engine.current_confidence
        assert conf2 > conf1

    def test_trend_detection_increasing(self):
        # Feed 10+ values to surpass the default window=10 threshold
        for v in [0.55, 0.58, 0.60, 0.62, 0.65, 0.68, 0.72, 0.78, 0.85, 0.95]:
            self.engine.update(v)
        assert self.engine.get_trend() == "increasing"

    def test_trend_detection_decreasing(self):
        self.engine.reset(0.95)
        for v in [0.88, 0.82, 0.75, 0.68, 0.60, 0.55, 0.50, 0.45, 0.40, 0.30]:
            self.engine.update(v)
        assert self.engine.get_trend() == "decreasing"

    def test_reset(self):
        self.engine.update(0.9)
        self.engine.reset()
        assert self.engine.current_confidence == 0.5
        assert len(self.engine._confidence_history) == 0


class TestEnsembleWrapper:
    def test_predict_proba_output_range(self):
        iso = IsolationForest(n_estimators=10, random_state=RANDOM_STATE)
        iso.fit(np.random.randn(30, 5))
        wrapper = EnsembleModelWrapper({"isolation_forest": iso})
        X = np.random.randn(10, 5)
        scores = wrapper.predict_proba(X)
        assert np.all(scores >= 0.0) and np.all(scores <= 1.0)

    def test_predict_output_shape(self):
        iso = IsolationForest(n_estimators=10, random_state=RANDOM_STATE)
        iso.fit(np.random.randn(30, 5))
        wrapper = EnsembleModelWrapper({"isolation_forest": iso})
        X = np.random.randn(5, 5)
        preds = wrapper.predict(X)
        assert preds.shape == (5,)
        assert set(preds.tolist()).issubset({0, 1})

    def test_decision_function(self):
        iso = IsolationForest(n_estimators=10, random_state=RANDOM_STATE)
        iso.fit(np.random.randn(30, 5))
        wrapper = EnsembleModelWrapper({"isolation_forest": iso})
        X = np.random.randn(5, 5)
        scores = wrapper.decision_function(X)
        assert scores.shape == (5,)

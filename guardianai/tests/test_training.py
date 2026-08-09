"""Tests for Model Training Engine and validation."""

import pytest
import numpy as np
from sklearn.ensemble import IsolationForest

from src.ai.validator import ModelValidator
from src.ai.model_wrapper import EnsembleModelWrapper
from src.utils.constants import RANDOM_STATE


class TestModelValidator:
    def setup_method(self):
        self.validator = ModelValidator()

    def test_validate_with_one_class_model(self):
        X_train = np.random.RandomState(RANDOM_STATE).randn(50, 10)
        model = IsolationForest(n_estimators=10, random_state=RANDOM_STATE)
        model.fit(X_train)
        X_val = np.random.RandomState(RANDOM_STATE+1).randn(20, 10)
        report = self.validator.validate(model, X_val)
        assert report["valid"] == True
        assert "accuracy" in report
        assert "far" in report
        assert "frr" in report
        assert "f1_score" in report

    def test_validate_ensemble_wrapper(self):
        X_train = np.random.RandomState(RANDOM_STATE).randn(50, 10)
        iso = IsolationForest(n_estimators=10, random_state=RANDOM_STATE)
        iso.fit(X_train)
        wrapper = EnsembleModelWrapper({"isolation_forest": iso})
        X_val = np.random.RandomState(RANDOM_STATE+1).randn(20, 10)
        report = self.validator.validate(wrapper, X_val)
        assert report["valid"] == True

    def test_validation_with_existing_accuracy(self):
        X = np.random.RandomState(RANDOM_STATE).randn(50, 10)
        model = IsolationForest(n_estimators=10, random_state=RANDOM_STATE)
        model.fit(X)
        X_val = np.random.RandomState(RANDOM_STATE+1).randn(20, 10)
        report = self.validator.validate(model, X_val, existing_accuracy=0.8)
        assert "improvement" in report
        assert "improved" in report


class TestEnsembleModelWrapper:
    def test_wrap_dict(self):
        iso = IsolationForest(n_estimators=10, random_state=RANDOM_STATE)
        iso.fit(np.random.randn(30, 5))
        wrapper = EnsembleModelWrapper({"isolation_forest": iso})
        X = np.random.randn(10, 5)
        scores = wrapper.predict_proba(X)
        assert scores.shape == (10,)
        assert np.all((scores >= 0) & (scores <= 1))

    def test_wrap_single_model(self):
        iso = IsolationForest(n_estimators=10, random_state=RANDOM_STATE)
        iso.fit(np.random.randn(30, 5))
        wrapper = EnsembleModelWrapper.wrap(iso)
        X = np.random.randn(5, 5)
        preds = wrapper.predict(X)
        assert preds.shape == (5,)

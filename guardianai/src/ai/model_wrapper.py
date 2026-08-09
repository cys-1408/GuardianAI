"""EnsembleModelWrapper - Wraps multiple sub-models into a unified prediction interface.

The training engine stores an ensemble of models (IsolationForest, OneClassSVM,
LightGBM) as a dictionary. This wrapper provides a single predict/predict_proba
interface so the InferenceEngine and ModelValidator can use it seamlessly.
"""

import logging
from typing import Any, Optional

import numpy as np

logger = logging.getLogger(__name__)


class EnsembleModelWrapper:
    """Wraps an ensemble of sub-models into a single predictable interface."""

    def __init__(self, model_dict: dict[str, Any]) -> None:
        self._models = model_dict
        self._lightgbm = model_dict.get("lightgbm")
        self._iso_forest = model_dict.get("isolation_forest")
        self._svm = model_dict.get("one_class_svm")
        self._feature_dim = model_dict.get("feature_dim", 0)

    @classmethod
    def wrap(cls, model: Any) -> "EnsembleModelWrapper":
        """Wrap a raw model object.

        Args:
            model: Either a dict (ensemble) or a single model object

        Returns:
            EnsembleModelWrapper instance
        """
        if isinstance(model, dict):
            return cls(model)
        return cls({"lightgbm": model})

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        """Get authentication probability scores.

        Uses LightGBM if available (primary classifier), otherwise
        falls back to IsolationForest or OneClassSVM scoring.

        Args:
            X: Feature matrix of shape (n_samples, n_features)

        Returns:
            Array of scores in [0, 1] for each sample
        """
        n = X.shape[0]
        scores = np.full(n, 0.5, dtype=np.float64)

        try:
            if self._lightgbm is not None and hasattr(self._lightgbm, "predict_proba"):
                proba = self._lightgbm.predict_proba(X)
                scores = proba[:, 1] if proba.shape[1] > 1 else proba[:, 0]
            elif self._iso_forest is not None:
                # IsolationForest: negative = anomaly -> lower score
                raw = self._iso_forest.score_samples(X)
                scores = 1.0 - (np.clip(raw, -10, 10) + 10) / 20
            elif self._svm is not None and hasattr(self._svm, "predict"):
                raw = self._svm.predict(X).astype(float)
                scores = np.clip((raw + 1) / 2, 0, 1)
        except Exception as e:
            logger.warning(f"Ensemble prediction failed: {e}")

        return np.clip(scores, 0.0, 1.0)

    def predict(self, X: np.ndarray) -> np.ndarray:
        """Get binary predictions (1=legitimate, 0=anomaly).

        Args:
            X: Feature matrix

        Returns:
            Array of predictions {0, 1}
        """
        scores = self.predict_proba(X)
        return (scores >= 0.5).astype(int)

    def decision_function(self, X: np.ndarray) -> np.ndarray:
        """Get raw decision scores (closer to 1 = more legitimate).

        Args:
            X: Feature matrix

        Returns:
            Array of decision values
        """
        return self.predict_proba(X)

    def score_samples(self, X: np.ndarray) -> np.ndarray:
        """Get raw sample scores if available (from IsolationForest).

        Args:
            X: Feature matrix

        Returns:
            Array of sample scores
        """
        if self._iso_forest is not None and hasattr(self._iso_forest, "score_samples"):
            return self._iso_forest.score_samples(X)
        return self.predict_proba(X)

    def __getstate__(self) -> dict:
        """For pickle serialization - return the underlying dict."""
        return self._models

    def __setstate__(self, state: dict) -> None:
        """For pickle deserialization."""
        self.__init__(state)

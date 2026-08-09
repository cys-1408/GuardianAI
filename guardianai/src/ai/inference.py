"""Inference Engine - Performs continuous behavioral authentication using the ML model."""

import logging
from typing import Any, Optional

import numpy as np

from src.utils.signals import get_signals
from src.ai.repository import ModelRepository
from src.ai.confidence import ConfidenceEngine
from src.ai.model_wrapper import EnsembleModelWrapper

logger = logging.getLogger(__name__)


class InferenceEngine:
    """Performs inference using the active ML model for continuous authentication."""

    def __init__(self, model_repo: ModelRepository,
                 confidence_engine: 'ConfidenceEngine') -> None:
        self._model_repo = model_repo
        self._confidence_engine = confidence_engine
        self._signals = get_signals()
        self._model_wrapper: Optional[EnsembleModelWrapper] = None
        self._model_version = None
        self._active = False

    def start(self) -> None:
        """Start the inference engine."""
        self._active = True
        self.load_production_model()
        logger.info("Inference engine started")

    def stop(self) -> None:
        """Stop the inference engine."""
        self._active = False
        logger.info("Inference engine stopped")

    def load_production_model(self) -> bool:
        """Load the current production model.

        Returns:
            True if model loaded successfully
        """
        model_data = self._model_repo.get_active_model()
        if model_data is None:
            logger.warning("No production model available")
            return False

        # Model is always stored as dict with sub-models; wrap it
        self._model_wrapper = EnsembleModelWrapper(model_data["model"])
        self._model_version = model_data.get("version", "unknown")
        logger.info(f"Production model loaded: v{self._model_version}")
        return True

    def predict(self, features: list[float]) -> Optional[dict[str, Any]]:
        """Run inference on a feature vector.

        Args:
            features: Normalized feature vector

        Returns:
            Prediction result or None on failure
        """
        if not self._active or self._model_wrapper is None:
            return None

        try:
            X = np.array([features], dtype=np.float64)
            score = float(self._model_wrapper.predict_proba(X)[0])
            label = int(score >= 0.5)

            result = {
                "score": score,
                "label": label,
                "model_version": self._model_version,
                "authenticated": score >= 0.5,
            }

            self._signals.inference_completed.emit(result)
            self._confidence_engine.update(score)
            return result

        except Exception as e:
            logger.error(f"Inference failed: {e}")
            return None

    def predict_batch(self, feature_vectors: list[list[float]]) -> list[float]:
        """Run inference on multiple feature vectors.

        Args:
            feature_vectors: List of normalized feature vectors

        Returns:
            List of prediction scores
        """
        results = []
        for fv in feature_vectors:
            result = self.predict(fv)
            if result:
                results.append(result["score"])
        return results

    def reload_model(self) -> bool:
        """Reload the production model (after retraining)."""
        return self.load_production_model()

    def get_status(self) -> dict[str, Any]:
        """Get inference engine status."""
        return {
            "active": self._active,
            "model_loaded": self._model_wrapper is not None,
            "model_version": self._model_version,
            "confidence": self._confidence_engine.current_confidence,
        }

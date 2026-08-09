"""Feature Normalization Engine - Standardizes extracted features for ML models."""

import logging
import statistics
from typing import Any, Optional

import numpy as np
from sklearn.preprocessing import StandardScaler, RobustScaler

from src.utils.signals import FeatureVector, get_signals
from src.utils.constants import TOTAL_FEATURES

logger = logging.getLogger(__name__)


class FeatureNormalizationEngine:
    """Normalizes and validates behavioral feature vectors."""

    def __init__(self) -> None:
        self._signals = get_signals()
        self._scaler: Optional[StandardScaler] = None
        self._robust_scaler: Optional[RobustScaler] = None
        self._feature_stats: dict[str, float] = {}
        self._is_fitted = False

    def fit(self, feature_vectors: list[list[float]]) -> None:
        """Fit normalization parameters from a dataset.

        Args:
            feature_vectors: List of raw feature vectors
        """
        if not feature_vectors:
            logger.warning("No feature vectors provided for normalization fit")
            return

        X = np.array(feature_vectors, dtype=np.float64)

        # Handle missing values
        X = np.nan_to_num(X, nan=0.0, posinf=0.0, neginf=0.0)

        self._scaler = StandardScaler()
        self._scaler.fit(X)

        self._robust_scaler = RobustScaler(quantile_range=(5, 95))
        self._robust_scaler.fit(X)

        # Store feature statistics
        self._feature_stats = {
            "mean": float(np.mean(X)),
            "std": float(np.std(X)),
            "min": float(np.min(X)),
            "max": float(np.max(X)),
            "num_features": X.shape[1] if X.ndim > 1 else X.shape[0],
            "num_samples": X.shape[0] if X.ndim > 1 else 1,
        }

        self._is_fitted = True
        logger.info(f"Normalization fitted: {self._feature_stats['num_samples']} samples, "
                    f"{self._feature_stats['num_features']} features")

    def normalize(self, raw_features: list[float]) -> Optional[list[float]]:
        """Normalize a raw feature vector.

        Args:
            raw_features: Raw feature vector

        Returns:
            Normalized feature vector or None on failure
        """
        if not raw_features:
            return None

        try:
            # Remove NaN and infinity values
            features = [0.0 if (not isinstance(f, (int, float)) or
                               math.isnan(f) or math.isinf(f))
                       else f for f in raw_features]

            X = np.array([features], dtype=np.float64)

            if self._is_fitted and self._scaler:
                X_norm = self._scaler.transform(X)
            else:
                # Fallback: min-max normalization
                arr = np.array(features)
                fmin, fmax = np.min(arr), np.max(arr)
                if fmax > fmin:
                    X_norm = (arr - fmin) / (fmax - fmin)
                else:
                    X_norm = np.zeros_like(arr)
                X_norm = X_norm.reshape(1, -1)

            normalized = X_norm[0].tolist()

            # Ensure consistent feature count
            if len(normalized) < TOTAL_FEATURES:
                normalized.extend([0.0] * (TOTAL_FEATURES - len(normalized)))
            elif len(normalized) > TOTAL_FEATURES:
                normalized = normalized[:TOTAL_FEATURES]

            return normalized

        except Exception as e:
            logger.error(f"Feature normalization failed: {e}")
            return None

    def normalize_batch(self, feature_vectors: list[list[float]]) -> list[list[float]]:
        """Normalize a batch of feature vectors.

        Args:
            feature_vectors: List of raw feature vectors

        Returns:
            List of normalized feature vectors
        """
        return [self.normalize(fv) for fv in feature_vectors
                if self.normalize(fv) is not None]

    def reset(self) -> None:
        """Reset normalization parameters."""
        self._scaler = None
        self._robust_scaler = None
        self._feature_stats = {}
        self._is_fitted = False
        logger.info("Normalization reset")

    def get_stats(self) -> dict[str, Any]:
        """Get normalization statistics."""
        return {
            "is_fitted": self._is_fitted,
            "feature_stats": self._feature_stats,
        }


import math

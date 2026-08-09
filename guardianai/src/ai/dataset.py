"""Dataset Manager - Organizes behavioral features into structured ML datasets."""

import json
import logging
import uuid
from datetime import datetime
from typing import Any, Optional

import numpy as np

from src.data.sqlite_manager import SQLiteManager
from src.data.behavioral_repo import BehavioralRepository
from src.utils.constants import DatasetType

logger = logging.getLogger(__name__)


class DatasetManager:
    """Manages behavioral datasets for ML training, validation, and retraining."""

    def __init__(self, db: SQLiteManager, behavior_repo: BehavioralRepository) -> None:
        self._db = db
        self._behavior_repo = behavior_repo

    def create_dataset(self, dataset_type: str, feature_vectors: list[list[float]],
                       feature_ids: Optional[list[str]] = None) -> Optional[str]:
        """Create a new dataset from feature vectors.

        Args:
            dataset_type: Type of dataset (enrollment, training, validation, retraining)
            feature_vectors: List of feature vectors
            feature_ids: Optional list of feature IDs

        Returns:
            Dataset ID if created successfully
        """
        try:
            dataset_id = str(uuid.uuid4())
            num_features = len(feature_vectors[0]) if feature_vectors else 0

            self._db.execute(
                """INSERT INTO datasets (dataset_id, dataset_type, creation_date,
                num_samples, feature_count, dataset_status)
                VALUES (?, ?, datetime('now'), ?, ?, 'created')""",
                (dataset_id, dataset_type, len(feature_vectors), num_features),
            )
            logger.info(f"Dataset {dataset_id} created: {dataset_type}, "
                       f"{len(feature_vectors)} samples, {num_features} features")
            return dataset_id

        except Exception as e:
            logger.error(f"Failed to create dataset: {e}")
            return None

    def get_enrollment_dataset(self) -> tuple[Optional[np.ndarray], Optional[str]]:
        """Get the enrollment dataset for initial training.

        Returns:
            Tuple of (feature_matrix, dataset_id) or (None, None)
        """
        rows = self._behavior_repo.get_features_by_date_range(
            datetime.min, datetime.now()
        )
        if not rows:
            return None, None

        features = []
        for row in rows:
            fv = row.get("feature_vector")
            if fv:
                try:
                    vec = json.loads(fv) if isinstance(fv, str) else fv
                    features.append(vec)
                except (json.JSONDecodeError, TypeError):
                    continue

        if not features:
            return None, None

        dataset_id = self.create_dataset(
            DatasetType.ENROLLMENT.value, features,
            [r["feature_id"] for r in rows if r.get("feature_vector")]
        )
        return np.array(features, dtype=np.float64), dataset_id

    def get_training_dataset(self) -> tuple[Optional[np.ndarray], Optional[np.ndarray],
                                            Optional[str]]:
        """Get training and validation datasets.

        Returns:
            Tuple of (X_train, X_val, dataset_id) or (None, None, None)
        """
        X, dataset_id = self.get_enrollment_dataset()
        if X is None or len(X) < 10:
            logger.warning("Insufficient data for training dataset")
            return None, None, None

        # Split into training and validation
        split_idx = int(len(X) * 0.8)
        X_train = X[:split_idx]
        X_val = X[split_idx:]

        return X_train, X_val, dataset_id

    def get_retraining_dataset(self, trusted_samples: list[dict]) -> Optional[np.ndarray]:
        """Create a retraining dataset from trusted samples.

        Args:
            trusted_samples: List of trusted feature data

        Returns:
            Feature matrix or None
        """
        features = []
        for sample in trusted_samples:
            fv = sample.get("feature_vector")
            if fv:
                try:
                    vec = json.loads(fv) if isinstance(fv, str) else fv
                    features.append(vec)
                except (json.JSONDecodeError, TypeError):
                    continue

        if not features:
            return None

        X = np.array(features, dtype=np.float64)
        dataset_id = self.create_dataset(
            DatasetType.RETRAINING.value, features
        )
        return X

    def get_dataset_stats(self) -> dict[str, Any]:
        """Get dataset statistics."""
        datasets = self._db.fetch_all(
            "SELECT * FROM datasets ORDER BY creation_date DESC"
        )
        return {
            "total_datasets": len(datasets),
            "datasets": datasets,
        }

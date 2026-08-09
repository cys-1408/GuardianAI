"""Model Training Engine - Builds personalized behavioral authentication models."""

import logging
import pickle
import time
import uuid
from datetime import datetime
from typing import Any, Optional

import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.svm import OneClassSVM
import lightgbm as lgb

from src.data.sqlite_manager import SQLiteManager
from src.ai.dataset import DatasetManager
from src.ai.repository import ModelRepository
from src.utils.constants import RANDOM_STATE, ANOMALY_CONTAMINATION

logger = logging.getLogger(__name__)


class ModelTrainingEngine:
    """Trains personalized ML models for behavioral authentication."""

    def __init__(self, db: SQLiteManager, dataset_mgr: DatasetManager,
                 model_repo: ModelRepository) -> None:
        self._db = db
        self._dataset_mgr = dataset_mgr
        self._model_repo = model_repo

    def train_initial_model(self) -> Optional[dict[str, Any]]:
        """Train the first authentication model after enrollment.

        Returns:
            Training report dict or None on failure
        """
        logger.info("Starting initial model training...")

        X_train, X_val, dataset_id = self._dataset_mgr.get_training_dataset()
        if X_train is None:
            logger.error("No training data available")
            return None

        return self._train_model(X_train, X_val, dataset_id, is_initial=True)

    def train_retraining_model(self, X_train: np.ndarray) -> Optional[dict[str, Any]]:
        """Train an updated model with new trusted data.

        Args:
            X_train: Training feature matrix

        Returns:
            Training report dict or None
        """
        if len(X_train) < 50:
            logger.warning(f"Insufficient retraining data: {len(X_train)} samples")
            return None

        split = int(len(X_train) * 0.8)
        X_tr = X_train[:split]
        X_va = X_train[split:]

        return self._train_model(X_tr, X_va, None, is_initial=False)

    def _train_model(self, X_train: np.ndarray, X_val: Optional[np.ndarray],
                     dataset_id: Optional[str],
                     is_initial: bool = False) -> Optional[dict[str, Any]]:
        """Internal training logic.

        Args:
            X_train: Training feature matrix
            X_val: Validation feature matrix
            dataset_id: Optional dataset ID
            is_initial: Whether this is initial training

        Returns:
            Training report
        """
        start_time = time.time()
        model_id = str(uuid.uuid4())

        try:
            # Train Isolation Forest for anomaly detection
            iso_forest = IsolationForest(
                n_estimators=100,
                contamination=ANOMALY_CONTAMINATION,
                random_state=RANDOM_STATE,
                n_jobs=-1,
            )
            iso_forest.fit(X_train)

            # Train One-Class SVM for boundary detection
            svm = OneClassSVM(
                nu=ANOMALY_CONTAMINATION,
                kernel='rbf',
                gamma='scale',
            )
            svm.fit(X_train)

            # Train LightGBM if enough samples
            lgb_model = None
            if len(X_train) >= 100:
                # Generate pseudo-labels for one-class classification
                y_train = np.ones(len(X_train))
                # Add small synthetic anomalies for training
                n_anomalies = max(1, int(len(X_train) * 0.1))
                noise = np.random.RandomState(RANDOM_STATE).normal(
                    0, 2, (n_anomalies, X_train.shape[1])
                )
                X_anom = X_train[:n_anomalies] + noise
                X_aug = np.vstack([X_train, X_anom])
                y_aug = np.hstack([np.ones(len(X_train)), np.zeros(n_anomalies)])

                lgb_model = lgb.LGBMClassifier(
                    n_estimators=100,
                    learning_rate=0.1,
                    num_leaves=31,
                    random_state=RANDOM_STATE,
                    n_jobs=-1,
                    verbose=-1,
                )
                lgb_model.fit(
                    X_aug, y_aug,
                    eval_set=[(X_aug, y_aug)],
                    eval_metric='auc',
                    callbacks=[lgb.early_stopping(10), lgb.log_evaluation(0)],
                )

            training_time = time.time() - start_time

            # Store the model (ensemble of iso_forest + svm + lgb)
            model_data = {
                "isolation_forest": iso_forest,
                "one_class_svm": svm,
                "lightgbm": lgb_model,
                "feature_dim": X_train.shape[1],
                "training_samples": len(X_train),
            }

            self._model_repo.store_model(
                model_id=model_id,
                model_data=model_data,
                version=1 if is_initial else None,
            )

            report = {
                "model_id": model_id,
                "training_time": training_time,
                "training_samples": len(X_train),
                "validation_samples": len(X_val) if X_val is not None else 0,
                "feature_dim": X_train.shape[1],
                "is_initial": is_initial,
                "dataset_id": dataset_id,
                "timestamp": datetime.now().isoformat(),
                "status": "completed",
            }

            # Record training history with numeric accuracy placeholder
            # (Actual validation accuracy will be updated after ModelValidator runs)
            initial_accuracy = "0.0"
            self._db.execute(
                """INSERT INTO training_history 
                (dataset_id, model_version, training_start, training_end, 
                 duration_seconds, validation_result)
                VALUES (?, ?, datetime('now'), datetime('now'), ?, ?)""",
                (dataset_id or "", str(report["model_id"]),
                 training_time, initial_accuracy),
            )

            logger.info(f"Model trained: {model_id} "
                       f"({len(X_train)} samples, {training_time:.2f}s)")
            return report

        except Exception as e:
            logger.error(f"Model training failed: {e}")
            return None

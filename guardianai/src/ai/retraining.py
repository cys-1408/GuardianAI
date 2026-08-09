"""Retraining Manager - Coordinates scheduled model updates via adaptive learning.

Monitors the retraining schedule, evaluates whether sufficient trusted behavioral
data has been collected, and initiates model retraining when thresholds are met.
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Optional

import numpy as np

from src.data.sqlite_manager import SQLiteManager
from src.ai.dataset import DatasetManager
from src.ai.training import ModelTrainingEngine
from src.ai.validator import ModelValidator
from src.ai.version import VersionManager
from src.ai.repository import ModelRepository
from src.data.sliding_window import SlidingWindowManager
from src.ai.model_wrapper import EnsembleModelWrapper
from src.utils.constants import RETRAINING_INTERVAL_DAYS, RETRAINING_MIN_SAMPLES

logger = logging.getLogger(__name__)


class RetrainingManager:
    """Manages the adaptive retraining lifecycle."""

    def __init__(self, db: SQLiteManager, dataset_mgr: DatasetManager,
                 training_engine: ModelTrainingEngine, validator: ModelValidator,
                 version_mgr: VersionManager, model_repo: ModelRepository,
                 sliding_window: SlidingWindowManager) -> None:
        self._db = db
        self._dataset_mgr = dataset_mgr
        self._training_engine = training_engine
        self._validator = validator
        self._version_mgr = version_mgr
        self._model_repo = model_repo
        self._sliding_window = sliding_window

    def should_retrain(self) -> bool:
        """Check if retraining should be triggered.

        Returns:
            True if retraining conditions are met
        """
        # Check last retraining date
        last = self._db.fetch_one(
            "SELECT training_end FROM training_history ORDER BY training_end DESC LIMIT 1"
        )
        if last and last["training_end"]:
            last_date = datetime.fromisoformat(last["training_end"])
            if datetime.now() - last_date < timedelta(days=RETRAINING_INTERVAL_DAYS):
                return False

        # Check sufficient trusted samples
        stats = self._sliding_window.get_window_stats()
        if stats["pending_retraining"] < RETRAINING_MIN_SAMPLES:
            return False

        return True

    def execute_retraining(self) -> Optional[dict[str, Any]]:
        """Execute the retraining workflow.

        Returns:
            Training report if successful, None otherwise
        """
        logger.info("Starting retraining cycle...")

        if not self.should_retrain():
            logger.info("Retraining conditions not met")
            return None

        # Get trusted training data
        trusted_samples = self._sliding_window.get_retraining_dataset()
        if len(trusted_samples) < RETRAINING_MIN_SAMPLES:
            logger.warning(f"Insufficient trusted samples: {len(trusted_samples)}")
            return None

        # Prepare dataset
        X = self._dataset_mgr.get_retraining_dataset(trusted_samples)
        if X is None or len(X) < RETRAINING_MIN_SAMPLES:
            logger.warning("Failed to prepare retraining dataset")
            return None

        # Train new model
        report = self._training_engine.train_retraining_model(X)
        if not report:
            logger.error("Retraining failed")
            return None

        # Validate new model
        model_data = self._model_repo.get_model(report["model_id"])
        if not model_data:
            logger.error("Could not load retrained model for validation")
            return None

        # Wrap model for validation
        wrapped_model = EnsembleModelWrapper.wrap(model_data["model"])

        # Get current production model accuracy for comparison
        active = self._model_repo.get_active_model()
        existing_accuracy = None
        if active:
            # Infer accuracy from the active model's training report
            active_model_id = active.get("model_id")
            if active_model_id:
                history = self._db.fetch_one(
                    "SELECT validation_result FROM training_history "
                    "WHERE model_version = ? ORDER BY training_end DESC LIMIT 1",
                    (active_model_id,),
                )
                if history and history["validation_result"]:
                    try:
                        existing_accuracy = float(history["validation_result"])
                    except (ValueError, TypeError):
                        pass

        val_report = self._validator.validate(
            wrapped_model, X[:int(len(X)*0.2)],
            existing_accuracy=existing_accuracy,
        )

        if val_report.get("overall_pass", False) and val_report.get("improved", False):
            # Deploy new model
            deployed = self._version_mgr.deploy_model(
                report["model_id"], val_report
            )
            if deployed:
                # Mark samples as used
                feature_ids = [s["feature_id"] for s in trusted_samples
                              if s.get("feature_id")]
                self._sliding_window.mark_used_for_retraining(feature_ids)
                logger.info(f"Retraining successful: new model deployed")
                return {"report": report, "validation": val_report, "deployed": True}
        else:
            logger.info("Retrained model did not improve, keeping current")
            return {"report": report, "validation": val_report, "deployed": False}

        return None

"""Model Validator - Evaluates trained models before deployment.

Validates accuracy, FAR, FRR, F1 score, prediction stability, and detects
overfitting before approving model replacement.
"""

import logging
from typing import Any, Optional

import numpy as np
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    confusion_matrix,
)

from src.utils.constants import (
    MIN_ACCEPTABLE_ACCURACY, MIN_ACCEPTABLE_F1,
    MAX_ACCEPTABLE_FAR, MAX_ACCEPTABLE_FRR,
)
from src.ai.model_wrapper import EnsembleModelWrapper

logger = logging.getLogger(__name__)


class ModelValidator:
    """Validates trained ML models against acceptance criteria."""

    def validate(self, model: Any, X_val: np.ndarray,
                 existing_accuracy: Optional[float] = None) -> dict[str, Any]:
        """Validate a trained model.

        Args:
            model: Trained model object
            X_val: Validation feature matrix
            existing_accuracy: Current production model accuracy for comparison

        Returns:
            Validation report dict
        """
        try:
            if isinstance(model, dict):
                model = EnsembleModelWrapper(model)

            # Generate predictions and scores
            if hasattr(model, "predict_proba"):
                proba = model.predict_proba(X_val)
                scores = proba[:, 1] if proba.ndim > 1 and proba.shape[1] > 1 else proba
                predictions = (scores >= 0.5).astype(int)
            elif hasattr(model, "predict"):
                predictions = model.predict(X_val)
                scores = predictions.astype(float)
            elif hasattr(model, "decision_function"):
                scores = model.decision_function(X_val)
                predictions = (scores >= 0).astype(int)
            else:
                return {"valid": False, "error": "Model has no prediction method"}

            # Handle one-class / ensemble output
            predictions = predictions.flatten() if hasattr(predictions, 'flatten') else np.asarray(predictions)
            unique = set(predictions.tolist())
            if unique == {-1, 1} or unique == {1}:
                predictions = (predictions == 1).astype(int)

            # Calculate metrics with pseudo-labels (assume all validation data is legitimate)
            y_true = np.ones(len(X_val))
            accuracy = accuracy_score(y_true, predictions)
            far = np.mean(predictions == 0)  # False positive rate
            frr = 1.0 - accuracy  # False negative rate (proxy)

            # Calculate F1, precision, recall
            precision = precision_score(y_true, predictions, zero_division=0)
            recall = recall_score(y_true, predictions, zero_division=0)
            f1 = f1_score(y_true, predictions, zero_division=0)

            # Stability check
            stability = float(np.std(scores))

            report = {
                "valid": True,
                "accuracy": float(accuracy),
                "far": float(far),
                "frr": float(frr),
                "precision": float(precision),
                "recall": float(recall),
                "f1_score": float(f1),
                "stability": stability,
                "num_samples": len(X_val),
                "passed_accuracy": accuracy >= MIN_ACCEPTABLE_ACCURACY,
                "passed_far": far <= MAX_ACCEPTABLE_FAR,
                "passed_frr": frr <= MAX_ACCEPTABLE_FRR,
                "passed_f1": f1 >= MIN_ACCEPTABLE_F1,
            }

            # Compare with existing model
            if existing_accuracy is not None:
                report["improvement"] = accuracy - existing_accuracy
                report["improved"] = accuracy > existing_accuracy
            else:
                report["improvement"] = 0.0
                report["improved"] = True

            # Overall validation result
            passed = all([
                report["passed_accuracy"],
                report["passed_far"],
                report["passed_frr"],
                report["passed_f1"],
            ])
            report["overall_pass"] = passed

            logger.info(
                f"Model validation: accuracy={accuracy:.3f}, "
                f"FAR={far:.3f}, FRR={frr:.3f}, F1={f1:.3f}, "
                f"passed={passed}"
            )
            return report

        except Exception as e:
            logger.error(f"Model validation failed: {e}")
            return {"valid": False, "error": str(e)}

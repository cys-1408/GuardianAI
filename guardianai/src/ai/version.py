"""Version Manager - Manages model lifecycle, versioning, and rollback operations."""

import logging
from typing import Any, Optional

from src.data.sqlite_manager import SQLiteManager
from src.ai.repository import ModelRepository

logger = logging.getLogger(__name__)


class VersionManager:
    """Tracks model versions, handles deployment and rollback."""

    def __init__(self, db: SQLiteManager, model_repo: ModelRepository) -> None:
        self._db = db
        self._model_repo = model_repo

    def deploy_model(self, model_id: str, validation_report: dict[str, Any]) -> bool:
        """Deploy a validated model to production.

        Args:
            model_id: Model to deploy
            validation_report: Validation results

        Returns:
            True if deployment succeeded
        """
        if not validation_report.get("overall_pass", False):
            logger.warning(f"Model {model_id} failed validation, not deploying")
            return False

        try:
            # Archive current model
            current = self._db.fetch_one(
                "SELECT model_id FROM models WHERE active_status = 1"
            )
            if current:
                self._db.execute(
                    "UPDATE models SET active_status = 0 WHERE model_id = ?",
                    (current["model_id"],),
                )

            # Deploy new model
            self._model_repo.set_active(model_id)

            # Update version record
            self._db.execute(
                """UPDATE model_versions 
                SET deployment_date = datetime('now'), 
                    validation_result = ?
                WHERE model_id = ?""",
                (str(validation_report.get("accuracy", 0)), model_id),
            )

            logger.info(f"Model {model_id} deployed to production")
            return True

        except Exception as e:
            logger.error(f"Model deployment failed: {e}")
            return False

    def rollback(self, model_id: str) -> bool:
        """Rollback to a specific model version.

        Args:
            model_id: Model to rollback to

        Returns:
            True if rollback succeeded
        """
        try:
            # Verify model exists
            model = self._model_repo.get_model(model_id)
            if not model:
                logger.error(f"Cannot rollback: model {model_id} not found")
                return False

            # Deactivate current
            self._db.execute("UPDATE models SET active_status = 0")

            # Activate rollback target
            self._model_repo.set_active(model_id)

            # Mark rollback in version history
            self._db.execute(
                "UPDATE model_versions SET rollback_status = 1 WHERE model_id = ?",
                (model_id,),
            )

            logger.info(f"Rolled back to model {model_id}")
            return True

        except Exception as e:
            logger.error(f"Rollback failed: {e}")
            return False

    def get_latest_version(self) -> Optional[str]:
        """Get the latest model version ID."""
        row = self._db.fetch_one(
            "SELECT model_id FROM models ORDER BY training_date DESC LIMIT 1"
        )
        return row["model_id"] if row else None

    def get_version_history(self) -> list[dict[str, Any]]:
        """Get complete version history."""
        return self._db.fetch_all(
            """SELECT mv.*, m.model_version, m.training_date, m.validation_status
            FROM model_versions mv
            JOIN models m ON mv.model_id = m.model_id
            ORDER BY mv.deployment_date DESC"""
        )

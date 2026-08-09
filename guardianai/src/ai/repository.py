"""Model Repository - Securely stores and manages ML model files and versioning."""

import logging
import pickle
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from src.data.sqlite_manager import SQLiteManager
from src.utils.constants import MODELS_DIR
from src.security.encryption import EncryptionManager

logger = logging.getLogger(__name__)


class ModelRepository:
    """Repository for trained ML model storage, versioning, and retrieval."""

    def __init__(self, db: SQLiteManager, encryption: Optional[EncryptionManager] = None) -> None:
        self._db = db
        self._encryption = encryption

    def store_model(self, model_id: str, model_data: dict[str, Any],
                    version: Optional[int] = None) -> bool:
        """Store a trained model.

        Args:
            model_id: Unique model identifier
            model_data: Model data dictionary containing the trained objects
            version: Optional version number (auto-increments if not provided)

        Returns:
            True if stored successfully
        """
        try:
            model_path = MODELS_DIR / f"{model_id}.pkl"

            # Serialize and optionally encrypt
            serialized = pickle.dumps(model_data)
            if self._encryption:
                serialized = self._encryption.encrypt(serialized)
            model_path.write_bytes(serialized)

            # Determine version
            if version is None:
                row = self._db.fetch_one(
                    "SELECT MAX(version_number) as max_ver FROM model_versions"
                )
                version = (row["max_ver"] or 0) + 1 if row else 1

            # Insert model record
            self._db.execute(
                """INSERT OR REPLACE INTO models 
                (model_id, model_version, training_date, active_status, validation_status, file_location)
                VALUES (?, ?, datetime('now'), 0, 'pending', ?)""",
                (model_id, str(version), str(model_path)),
            )

            # Insert version record
            self._db.execute(
                """INSERT INTO model_versions (model_id, version_number, deployment_date, rollback_status)
                VALUES (?, ?, datetime('now'), 0)""",
                (model_id, version),
            )

            logger.info(f"Model {model_id} v{version} stored at {model_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to store model: {e}")
            return False

    def get_active_model(self) -> Optional[dict[str, Any]]:
        """Get the currently active production model.

        Returns:
            Model data dict with 'model' and 'version' keys, or None
        """
        try:
            row = self._db.fetch_one(
                "SELECT * FROM models WHERE active_status = 1 ORDER BY training_date DESC LIMIT 1"
            )
            if not row:
                return None

            model_path = Path(row["file_location"])
            if not model_path.exists():
                logger.warning(f"Model file not found: {model_path}")
                return None

            serialized = model_path.read_bytes()
            if self._encryption:
                serialized = self._encryption.decrypt(serialized)
            model_data = pickle.loads(serialized)

            return {
                "model": model_data,
                "model_id": row["model_id"],
                "version": row["model_version"],
                "training_date": row["training_date"],
            }

        except Exception as e:
            logger.error(f"Failed to load active model: {e}")
            return None

    def get_model(self, model_id: str) -> Optional[dict[str, Any]]:
        """Get a specific model by ID.

        Args:
            model_id: Model identifier

        Returns:
            Model data or None
        """
        try:
            row = self._db.fetch_one(
                "SELECT * FROM models WHERE model_id = ?", (model_id,)
            )
            if not row:
                return None

            model_path = Path(row["file_location"])
            if not model_path.exists():
                return None

            serialized = model_path.read_bytes()
            if self._encryption:
                serialized = self._encryption.decrypt(serialized)
            model_data = pickle.loads(serialized)

            return {
                "model": model_data,
                "model_id": row["model_id"],
                "version": row["model_version"],
            }

        except Exception as e:
            logger.error(f"Failed to load model {model_id}: {e}")
            return None

    def set_active(self, model_id: str) -> bool:
        """Set a model as the active production model.

        Args:
            model_id: Model to activate

        Returns:
            True if activation succeeded
        """
        try:
            # Deactivate all models
            self._db.execute("UPDATE models SET active_status = 0")
            # Activate specified model
            self._db.execute(
                "UPDATE models SET active_status = 1, validation_status = 'production' WHERE model_id = ?",
                (model_id,),
            )
            logger.info(f"Model {model_id} set as active")
            return True
        except Exception as e:
            logger.error(f"Failed to activate model: {e}")
            return False

    def get_model_history(self) -> list[dict[str, Any]]:
        """Get history of all models.

        Returns:
            List of model metadata dicts
        """
        return self._db.fetch_all(
            "SELECT * FROM models ORDER BY training_date DESC"
        )

    def delete_model(self, model_id: str) -> bool:
        """Delete a model.

        Args:
            model_id: Model to delete

        Returns:
            True if deleted
        """
        try:
            row = self._db.fetch_one(
                "SELECT file_location FROM models WHERE model_id = ?", (model_id,)
            )
            if row:
                Path(row["file_location"]).unlink(missing_ok=True)
            self._db.execute("DELETE FROM models WHERE model_id = ?", (model_id,))
            self._db.execute(
                "DELETE FROM model_versions WHERE model_id = ?", (model_id,)
            )
            logger.info(f"Model {model_id} deleted")
            return True
        except Exception as e:
            logger.error(f"Failed to delete model: {e}")
            return False

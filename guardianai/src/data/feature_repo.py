"""Feature Repository - Stores and provides structured access to normalized features."""

import json
import logging
from datetime import datetime
from typing import Any, Optional

from src.data.sqlite_manager import SQLiteManager

logger = logging.getLogger(__name__)


class FeatureRepository:
    """Repository for normalized behavioral feature vectors."""

    def __init__(self, db: SQLiteManager) -> None:
        self._db = db

    def store_features(self, feature_id: str, features: list[float],
                       metadata: Optional[dict] = None) -> bool:
        """Store normalized feature data.

        Args:
            feature_id: Feature identifier
            features: Normalized feature vector
            metadata: Optional metadata

        Returns:
            True if stored successfully
        """
        try:
            self._db.execute(
                "UPDATE behavioral_features SET feature_vector = ? WHERE feature_id = ?",
                (json.dumps(features), feature_id),
            )
            return True
        except Exception as e:
            logger.error(f"Failed to store features: {e}")
            return False

    def get_features(self, feature_id: str) -> Optional[list[float]]:
        """Get a feature vector by ID.

        Args:
            feature_id: Feature identifier

        Returns:
            Feature vector or None
        """
        row = self._db.fetch_one(
            "SELECT feature_vector FROM behavioral_features WHERE feature_id = ?",
            (feature_id,),
        )
        if row and row["feature_vector"]:
            return json.loads(row["feature_vector"])
        return None

    def get_all_feature_vectors(self, trust_level: Optional[str] = None,
                                limit: int = 10000) -> list[dict[str, Any]]:
        """Get all feature vectors, optionally filtered by trust level.

        Args:
            trust_level: Optional trust level filter
            limit: Maximum results

        Returns:
            List of feature data with vectors
        """
        if trust_level:
            rows = self._db.fetch_all(
                """SELECT feature_id, timestamp, feature_vector, trust_level 
                FROM behavioral_features WHERE trust_level = ? 
                AND feature_vector IS NOT NULL
                ORDER BY timestamp DESC LIMIT ?""",
                (trust_level, limit),
            )
        else:
            rows = self._db.fetch_all(
                """SELECT feature_id, timestamp, feature_vector, trust_level 
                FROM behavioral_features WHERE feature_vector IS NOT NULL
                ORDER BY timestamp DESC LIMIT ?""",
                (limit,),
            )
        result = []
        for row in rows:
            if row["feature_vector"]:
                row["feature_vector"] = json.loads(row["feature_vector"])
                result.append(row)
        return result

    def get_feature_count(self) -> int:
        """Get count of stored feature vectors."""
        row = self._db.fetch_one(
            "SELECT COUNT(*) as count FROM behavioral_features WHERE feature_vector IS NOT NULL"
        )
        return row["count"] if row else 0

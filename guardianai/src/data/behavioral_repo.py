"""Behavioral Repository - Stores and retrieves behavioral feature vectors.

Maintains behavioral information for authentication and adaptive learning
with indexing by timestamps, session identifiers, and trust status.
"""

import json
import logging
import uuid
from datetime import datetime
from typing import Any, Optional

from src.data.sqlite_manager import SQLiteManager, DatabaseError
from src.utils.signals import FeatureVector

logger = logging.getLogger(__name__)


class BehavioralRepository:
    """Repository for behavioral feature storage and retrieval."""

    def __init__(self, db: SQLiteManager) -> None:
        self._db = db

    def store_feature(self, feature: FeatureVector, trust_level: str = "medium") -> Optional[str]:
        """Store a behavioral feature vector.

        Args:
            feature: The feature vector to store
            trust_level: Trust classification

        Returns:
            Feature ID if stored successfully, None otherwise
        """
        try:
            feature_id = str(uuid.uuid4())
            self._db.execute(
                """INSERT INTO behavioral_features 
                (feature_id, session_id, timestamp, keyboard_features, mouse_features,
                 scroll_features, session_features, statistical_features, feature_vector, trust_level)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    feature_id,
                    feature.session_id,
                    feature.timestamp.isoformat(),
                    json.dumps({}),  # individual feature groups stored separately
                    json.dumps({}),
                    json.dumps({}),
                    json.dumps({}),
                    json.dumps({}),
                    json.dumps(feature.features),
                    trust_level,
                ),
            )
            return feature_id
        except DatabaseError as e:
            logger.error(f"Failed to store feature: {e}")
            return None

    def get_feature(self, feature_id: str) -> Optional[dict[str, Any]]:
        """Retrieve a feature vector by ID.

        Args:
            feature_id: Feature identifier

        Returns:
            Feature data dict or None
        """
        return self._db.fetch_one(
            "SELECT * FROM behavioral_features WHERE feature_id = ?",
            (feature_id,),
        )

    def get_features_by_session(self, session_id: str) -> list[dict[str, Any]]:
        """Get all features for a session.

        Args:
            session_id: Session identifier

        Returns:
            List of feature dicts
        """
        return self._db.fetch_all(
            "SELECT * FROM behavioral_features WHERE session_id = ? ORDER BY timestamp",
            (session_id,),
        )

    def get_features_by_date_range(
        self, start: datetime, end: datetime
    ) -> list[dict[str, Any]]:
        """Get features within a date range.

        Args:
            start: Start datetime
            end: End datetime

        Returns:
            List of feature dicts
        """
        return self._db.fetch_all(
            """SELECT * FROM behavioral_features 
            WHERE timestamp >= ? AND timestamp <= ? 
            ORDER BY timestamp""",
            (start.isoformat(), end.isoformat()),
        )

    def get_trusted_features(self, limit: int = 1000) -> list[dict[str, Any]]:
        """Get features with trust level 'high'.

        Args:
            limit: Maximum number of features to return

        Returns:
            List of trusted feature dicts
        """
        return self._db.fetch_all(
            """SELECT bf.* FROM behavioral_features bf
            INNER JOIN trusted_features tf ON bf.feature_id = tf.feature_id
            ORDER BY bf.timestamp DESC LIMIT ?""",
            (limit,),
        )

    def mark_trusted(self, feature_id: str, trust_score: float) -> bool:
        """Mark a feature as trusted for adaptive learning.

        Args:
            feature_id: Feature to mark
            trust_score: Associated trust score

        Returns:
            True if marked successfully
        """
        try:
            self._db.execute(
                """INSERT INTO trusted_features 
                (feature_id, trust_score, collection_date, retraining_status)
                VALUES (?, ?, datetime('now'), 'pending')""",
                (feature_id, trust_score),
            )
            self._db.execute(
                "UPDATE behavioral_features SET trust_level = 'high' WHERE feature_id = ?",
                (feature_id,),
            )
            return True
        except DatabaseError as e:
            logger.error(f"Failed to mark feature trusted: {e}")
            return False

    def get_feature_count(self) -> int:
        """Get total number of stored features."""
        row = self._db.fetch_one("SELECT COUNT(*) as count FROM behavioral_features")
        return row["count"] if row else 0

    def get_trusted_count(self) -> int:
        """Get number of trusted features."""
        row = self._db.fetch_one(
            "SELECT COUNT(*) as count FROM trusted_features"
        )
        return row["count"] if row else 0

    def delete_old_features(self, before: datetime) -> int:
        """Delete features older than a given date.

        Args:
            before: Delete features before this datetime

        Returns:
            Number of deleted features
        """
        self._db.execute(
            "DELETE FROM behavioral_features WHERE timestamp < ?",
            (before.isoformat(),),
        )
        return self._db._get_connection().total_changes  # type: ignore

"""Sliding Window Manager - Maintains evolving behavioral dataset.

Prevents outdated behavioral patterns from influencing future models by
retaining only recent trusted behavioral information within configurable
time and size limits.
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Optional

from src.data.sqlite_manager import SQLiteManager
from src.data.behavioral_repo import BehavioralRepository

logger = logging.getLogger(__name__)


class SlidingWindowManager:
    """Manages the sliding behavioral repository for adaptive learning."""

    def __init__(self, db: SQLiteManager, behavior_repo: BehavioralRepository) -> None:
        self._db = db
        self._behavior_repo = behavior_repo
        self._window_days: int = 90
        self._max_samples: int = 10000

    def configure(self, window_days: int, max_samples: int) -> None:
        """Configure sliding window parameters.

        Args:
            window_days: Retention period in days
            max_samples: Maximum number of samples to retain
        """
        self._window_days = window_days
        self._max_samples = max_samples
        logger.info(f"Sliding window configured: {window_days}d, {max_samples} max")

    def add_trusted_sample(self, feature_id: str, trust_score: float) -> bool:
        """Add a trusted behavioral sample.

        Args:
            feature_id: Feature identifier
            trust_score: Trust score for this sample

        Returns:
            True if added successfully
        """
        try:
            self._behavior_repo.mark_trusted(feature_id, trust_score)
            self._maintain_window()
            return True
        except Exception as e:
            logger.error(f"Failed to add trusted sample: {e}")
            return False

    def _maintain_window(self) -> None:
        """Maintain the sliding window by removing obsolete data."""
        try:
            # Remove samples outside the time window
            cutoff = datetime.now() - timedelta(days=self._window_days)
            self._db.execute(
                """DELETE FROM trusted_features 
                WHERE collection_date < ?""",
                (cutoff.isoformat(),),
            )

            # Enforce maximum sample count
            count_row = self._db.fetch_one(
                "SELECT COUNT(*) as count FROM trusted_features"
            )
            current_count = count_row["count"] if count_row else 0

            if current_count > self._max_samples:
                excess = current_count - self._max_samples
                self._db.execute(
                    """DELETE FROM trusted_features 
                    WHERE trusted_feature_id IN (
                        SELECT trusted_feature_id FROM trusted_features 
                        ORDER BY collection_date ASC LIMIT ?
                    )""",
                    (excess,),
                )
                logger.debug(f"Removed {excess} excess trusted samples")

        except Exception as e:
            logger.error(f"Sliding window maintenance failed: {e}")

    def get_retraining_dataset(self, min_samples: int = 100) -> list[dict[str, Any]]:
        """Get trusted features eligible for retraining.

        Args:
            min_samples: Minimum samples required

        Returns:
            List of trusted feature dicts
        """
        rows = self._db.fetch_all(
            """SELECT bf.*, tf.trust_score, tf.collection_date 
            FROM behavioral_features bf
            INNER JOIN trusted_features tf ON bf.feature_id = tf.feature_id
            WHERE tf.retraining_status = 'pending'
            ORDER BY tf.collection_date DESC
            LIMIT ?""",
            (self._max_samples,),
        )
        return rows

    def get_window_stats(self) -> dict[str, Any]:
        """Get sliding window statistics."""
        total = self._db.fetch_one(
            "SELECT COUNT(*) as count FROM trusted_features"
        )
        pending = self._db.fetch_one(
            "SELECT COUNT(*) as count FROM trusted_features WHERE retraining_status = 'pending'"
        )
        oldest = self._db.fetch_one(
            "SELECT MIN(collection_date) as oldest FROM trusted_features"
        )
        newest = self._db.fetch_one(
            "SELECT MAX(collection_date) as newest FROM trusted_features"
        )
        return {
            "total_trusted": total["count"] if total else 0,
            "pending_retraining": pending["count"] if pending else 0,
            "oldest_sample": oldest["oldest"] if oldest else None,
            "newest_sample": newest["newest"] if newest else None,
            "window_days": self._window_days,
            "max_samples": self._max_samples,
        }

    def mark_used_for_retraining(self, feature_ids: list[str]) -> None:
        """Mark trusted features as used for retraining.

        Args:
            feature_ids: List of feature IDs that were used
        """
        for fid in feature_ids:
            try:
                self._db.execute(
                    "UPDATE trusted_features SET retraining_status = 'used' WHERE feature_id = ?",
                    (fid,),
                )
            except Exception as e:
                logger.warning(f"Failed to mark feature {fid}: {e}")

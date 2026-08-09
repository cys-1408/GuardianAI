"""Training Scheduler - Determines when ML models should be trained or retrained.

Evaluates system workload, user activity, and training intervals to schedule
model training without affecting normal desktop usage.
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Optional

from src.data.sqlite_manager import SQLiteManager
from src.application.session import SessionManager
from src.utils.constants import RETRAINING_INTERVAL_DAYS, RETRAINING_MIN_SAMPLES

logger = logging.getLogger(__name__)


class TrainingScheduler:
    """Schedules ML training operations based on system conditions."""

    def __init__(self, db: SQLiteManager, session_mgr: SessionManager) -> None:
        self._db = db
        self._session = session_mgr

    def should_schedule_initial_training(self) -> bool:
        """Check if initial model training should start.

        Returns:
            True if enrollment is complete and no model exists
        """
        # Check if any model exists
        model = self._db.fetch_one(
            "SELECT COUNT(*) as count FROM models"
        )
        if model and model["count"] > 0:
            return False

        # Check enrollment status
        enrollment = self._db.fetch_one(
            "SELECT completion_status FROM enrollment ORDER BY enrollment_id DESC LIMIT 1"
        )
        return enrollment and enrollment["completion_status"] == "completed"

    def should_schedule_retraining(self) -> bool:
        """Check if monthly retraining should be scheduled.

        Returns:
            True if retraining conditions are suitable
        """
        # Check retraining interval
        last = self._db.fetch_one(
            "SELECT training_end FROM training_history ORDER BY training_end DESC LIMIT 1"
        )
        if last and last["training_end"]:
            last_date = datetime.fromisoformat(last["training_end"])
            if datetime.now() - last_date < timedelta(days=RETRAINING_INTERVAL_DAYS):
                return False

        # Check sufficient trusted data
        trusted = self._db.fetch_one(
            "SELECT COUNT(*) as count FROM trusted_features WHERE retraining_status = 'pending'"
        )
        if not trusted or trusted["count"] < RETRAINING_MIN_SAMPLES:
            return False

        # Check system is not under heavy load (rolling events-per-minute)
        session = self._session.current_session
        if session:
            # Calculate recent event rate: if > 50 events/min, defer retraining
            now = datetime.now()
            recent_features = self._db.fetch_one(
                "SELECT COUNT(*) as count FROM behavioral_features "
                "WHERE timestamp > datetime('now', '-1 minute')"
            )
            if recent_features and recent_features["count"] > 50:
                logger.debug("Deferring retraining: user is very active")
                return False

        return True

    def get_next_scheduled_training(self) -> Optional[datetime]:
        """Get the next scheduled training time.

        Returns:
            Datetime of next scheduled training or None
        """
        last = self._db.fetch_one(
            "SELECT training_end FROM training_history ORDER BY training_end DESC LIMIT 1"
        )
        if last and last["training_end"]:
            return datetime.fromisoformat(last["training_end"]) + timedelta(
                days=RETRAINING_INTERVAL_DAYS
            )
        return datetime.now()

    def get_schedule_status(self) -> dict[str, Any]:
        """Get training schedule status."""
        return {
            "initial_training_due": self.should_schedule_initial_training(),
            "retraining_due": self.should_schedule_retraining(),
            "next_scheduled": self.get_next_scheduled_training(),
        }

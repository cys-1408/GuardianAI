"""Enrollment Validator - Verifies enrollment data quality and completeness."""

import logging
from typing import Any, Optional

from src.data.sqlite_manager import SQLiteManager
from src.utils.constants import ENROLLMENT_DAYS, ENROLLMENT_REQUIRED_SESSIONS

logger = logging.getLogger(__name__)


class EnrollmentValidator:
    """Validates enrollment data before allowing model training."""

    def __init__(self, db: SQLiteManager) -> None:
        self._db = db

    def validate(self) -> bool:
        """Validate that enrollment collected sufficient data.

        Checks:
        - All 7 assignments completed
        - Sufficient behavioral features collected
        - Minimum feature diversity achieved

        Returns:
            True if enrollment data is sufficient
        """
        checks = [
            self._check_assignments_completed(),
            self._check_minimum_features(),
            self._check_feature_diversity(),
        ]
        passed = all(checks)
        if passed:
            logger.info("Enrollment validation passed")
        else:
            logger.warning(f"Enrollment validation failed: {checks}")
        return passed

    def _check_assignments_completed(self) -> bool:
        """Check all required assignments are completed."""
        total = self._db.fetch_one(
            "SELECT COUNT(*) as count FROM assignments"
        )
        completed = self._db.fetch_one(
            """SELECT COUNT(*) as count FROM assignment_progress ap
            JOIN assignments a ON ap.assignment_id = a.assignment_id
            WHERE ap.validation_status = 'completed'"""
        )
        t = total["count"] if total else 0
        c = completed["count"] if completed else 0
        return t > 0 and c >= t

    def _check_minimum_features(self) -> bool:
        """Check minimum number of behavioral features collected."""
        row = self._db.fetch_one(
            "SELECT COUNT(*) as count FROM behavioral_features"
        )
        count = row["count"] if row else 0
        return count >= 50  # Minimum 50 feature vectors

    def _check_feature_diversity(self) -> bool:
        """Check that features have adequate diversity."""
        row = self._db.fetch_one(
            "SELECT COUNT(DISTINCT session_id) as count FROM behavioral_features"
        )
        sessions = row["count"] if row else 0
        return sessions >= ENROLLMENT_REQUIRED_SESSIONS  # At least 7 different sessions

    def get_report(self) -> dict[str, Any]:
        """Get detailed validation report."""
        return {
            "assignments_completed": self._check_assignments_completed(),
            "minimum_features": self._check_minimum_features(),
            "feature_diversity": self._check_feature_diversity(),
            "overall": self.validate(),
        }

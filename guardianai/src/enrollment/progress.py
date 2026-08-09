"""Progress Manager - Tracks enrollment progress throughout the 7-day period."""

import logging
from typing import Any, Optional

from src.data.sqlite_manager import SQLiteManager
from src.utils.constants import ENROLLMENT_DAYS

logger = logging.getLogger(__name__)


class ProgressManager:
    """Tracks enrollment completion progress."""

    def __init__(self, db: SQLiteManager) -> None:
        self._db = db

    def calculate(self, user_id: Optional[str] = None) -> float:
        """Calculate overall enrollment progress as a percentage [0.0, 1.0].

        Args:
            user_id: Optional user filter

        Returns:
            Progress value from 0.0 to 1.0
        """
        total = self._db.fetch_one(
            "SELECT COUNT(*) as count FROM assignments"
        )
        completed = self._db.fetch_one(
            """SELECT COUNT(*) as count FROM assignment_progress ap
            JOIN assignments a ON ap.assignment_id = a.assignment_id
            WHERE ap.validation_status = 'completed'"""
        )
        total_count = total["count"] if total else ENROLLMENT_DAYS
        completed_count = completed["count"] if completed else 0

        if total_count == 0:
            return 0.0
        return min(1.0, completed_count / total_count)

    def get_today_progress(self, day: int) -> float:
        """Get progress for a specific day.

        Args:
            day: Day number (1-7)

        Returns:
            Progress for that day [0.0, 1.0]
        """
        row = self._db.fetch_one(
            """SELECT ap.completion_percentage FROM assignment_progress ap
            JOIN assignments a ON ap.assignment_id = a.assignment_id
            WHERE a.day_number = ?""",
            (day,),
        )
        if row and row["completion_percentage"]:
            return row["completion_percentage"] / 100.0
        return 0.0

    def get_days_remaining(self) -> int:
        """Get number of days remaining in enrollment.

        Returns:
            Days remaining
        """
        completed = self._db.fetch_one(
            "SELECT COUNT(*) as count FROM assignments a "
            "JOIN assignment_progress ap ON a.assignment_id = ap.assignment_id "
            "WHERE ap.validation_status = 'completed'"
        )
        completed_count = completed["count"] if completed else 0
        return max(0, ENROLLMENT_DAYS - completed_count)

    def get_stats(self) -> dict[str, Any]:
        """Get progress statistics."""
        return {
            "progress": self.calculate(),
            "days_remaining": self.get_days_remaining(),
            "total_days": ENROLLMENT_DAYS,
        }

"""Enrollment Manager - Orchestrates the 7-day behavioral enrollment process."""

import logging
import uuid
from datetime import datetime, timedelta
from typing import Any, Optional

from src.data.sqlite_manager import SQLiteManager
from src.enrollment.assignments import AssignmentManager
from src.enrollment.progress import ProgressManager
from src.enrollment.calendar import CalendarManager
from src.enrollment.validator import EnrollmentValidator
from src.utils.signals import get_signals
from src.utils.constants import EnrollmentStatus, ENROLLMENT_DAYS

logger = logging.getLogger(__name__)


class EnrollmentManager:
    """Controls the complete one-week enrollment process."""

    def __init__(self, db: SQLiteManager, assignment_mgr: AssignmentManager,
                 progress_mgr: ProgressManager, calendar_mgr: CalendarManager,
                 validator: EnrollmentValidator) -> None:
        self._db = db
        self._assignments = assignment_mgr
        self._progress = progress_mgr
        self._calendar = calendar_mgr
        self._validator = validator
        self._signals = get_signals()
        self._enrollment_id: Optional[int] = None
        self._user_id: Optional[str] = None
        self._status: str = EnrollmentStatus.NOT_STARTED.value

    @property
    def status(self) -> str:
        return self._status

    @property
    def is_active(self) -> bool:
        return self._status == EnrollmentStatus.IN_PROGRESS.value

    def start_enrollment(self, user_id: str) -> bool:
        """Start the enrollment process for a user.

        Args:
            user_id: User to enroll

        Returns:
            True if enrollment started
        """
        try:
            self._user_id = user_id
            self._status = EnrollmentStatus.IN_PROGRESS.value

            enroll_id = self._db.insert(
                """INSERT INTO enrollment (user_id, start_date, current_day, completion_status)
                VALUES (?, datetime('now'), 1, 'in_progress')""",
                (user_id,),
            )
            self._enrollment_id = enroll_id

            # Generate assignments for all 7 days
            self._assignments.generate_all(user_id)
            self._calendar.start_schedule(user_id)

            self._signals.enrollment_started.emit()
            logger.info(f"Enrollment started for user {user_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to start enrollment: {e}")
            return False

    def get_current_day(self) -> int:
        """Get the current enrollment day number."""
        row = self._db.fetch_one(
            "SELECT current_day FROM enrollment WHERE enrollment_id = ?",
            (self._enrollment_id,),
        )
        return row["current_day"] if row else 1

    def advance_day(self) -> bool:
        """Advance to the next enrollment day.

        Returns:
            True if advanced successfully
        """
        current = self.get_current_day()
        if current >= ENROLLMENT_DAYS:
            return self.complete_enrollment()

        try:
            self._db.execute(
                "UPDATE enrollment SET current_day = ? WHERE enrollment_id = ?",
                (current + 1, self._enrollment_id),
            )
            return True
        except Exception as e:
            logger.error(f"Failed to advance enrollment day: {e}")
            return False

    def complete_enrollment(self) -> bool:
        """Mark enrollment as completed.

        Returns:
            True if validation passed and enrollment completed
        """
        if not self._validator.validate():
            logger.warning("Enrollment validation failed")
            return False

        try:
            self._db.execute(
                """UPDATE enrollment SET 
                completion_date = datetime('now'), completion_status = 'completed'
                WHERE enrollment_id = ?""",
                (self._enrollment_id,),
            )
            self._status = EnrollmentStatus.COMPLETED.value
            self._signals.enrollment_completed.emit()
            logger.info("Enrollment completed successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to complete enrollment: {e}")
            return False

    def mark_completed(self) -> None:
        """Force-mark enrollment as completed (used for session-based completion).

        This is a public setter used when the system determines enrollment
        should be marked complete based on session count (7+ sessions) even
        if the standard assignment path hasn't finished.
        Persists to DB and emits completion signal.
        """
        self._status = EnrollmentStatus.COMPLETED.value
        try:
            self._db.execute(
                """UPDATE enrollment SET 
                completion_date = datetime('now'), completion_status = 'completed'
                WHERE enrollment_id = ?""",
                (self._enrollment_id,),
            )
        except Exception as e:
            logger.warning(f"Could not update enrollment DB record: {e}")
        logger.info("Enrollment marked as completed (session-based gate)")
        self._signals.enrollment_completed.emit()

    def get_progress(self) -> float:
        """Get overall enrollment progress [0.0, 1.0]."""
        return self._progress.calculate()

    def get_stats(self) -> dict[str, Any]:
        """Get enrollment statistics."""
        return {
            "status": self._status,
            "current_day": self.get_current_day(),
            "total_days": ENROLLMENT_DAYS,
            "progress": self.get_progress(),
            "user_id": self._user_id,
        }

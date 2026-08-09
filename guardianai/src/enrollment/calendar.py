"""Calendar Manager - Maintains the enrollment schedule and daily timeline."""

import logging
from datetime import datetime, timedelta
from typing import Any, Optional

from src.data.sqlite_manager import SQLiteManager

logger = logging.getLogger(__name__)


class CalendarManager:
    """Manages the enrollment schedule, reminders, and timeline tracking."""

    def __init__(self, db: SQLiteManager) -> None:
        self._db = db

    def start_schedule(self, user_id: str) -> bool:
        """Start the enrollment schedule for a user.

        Args:
            user_id: User identifier

        Returns:
            True if schedule started
        """
        logger.info(f"Enrollment schedule started for user {user_id}")
        return True

    def get_current_day_dates(self) -> dict[str, Any]:
        """Get start and end dates for each enrollment day.

        Returns:
            Dict with start_date and completion_target dates
        """
        row = self._db.fetch_one(
            "SELECT start_date FROM enrollment ORDER BY enrollment_id DESC LIMIT 1"
        )
        if not row:
            return {}
        start = datetime.fromisoformat(row["start_date"])
        return {
            "start_date": start.isoformat(),
            "completion_target": (start + timedelta(days=7)).isoformat(),
        }

    def get_reminder_message(self, day: int) -> str:
        """Get a reminder message for the current day.

        Args:
            day: Current enrollment day

        Returns:
            Reminder message string
        """
        messages = {
            1: "Time for your Natural Typing Assessment! Spend 25 minutes typing naturally.",
            2: "Your Copy Typing Assessment awaits! Copy the provided text for 20 minutes.",
            3: "Mouse Interaction time! Complete the clicking and dragging tasks.",
            4: "Scrolling & Navigation Assessment ready! Browse and read for 20 minutes.",
            5: "Mixed Productivity Assessment! Perform various desktop activities.",
            6: "Free Usage Observation day - just use your computer normally.",
            7: "Final day! GuardianAI will now train your authentication model.",
        }
        return messages.get(day, f"Complete your Day {day} enrollment assignment.")

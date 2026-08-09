"""Assignment Manager - Creates and schedules daily enrollment assignments."""

import logging
import uuid
from typing import Any, Optional

from src.data.sqlite_manager import SQLiteManager

logger = logging.getLogger(__name__)

DAILY_ASSIGNMENTS = [
    {"day": 1, "name": "Natural Typing Assessment", "type": "typing", 
     "duration": 25, "criteria": "min_typing_seconds=300"},
    {"day": 2, "name": "Copy Typing Assessment", "type": "copy_typing",
     "duration": 20, "criteria": "paragraphs_completed=3"},
    {"day": 3, "name": "Mouse Interaction Assessment", "type": "mouse",
     "duration": 20, "criteria": "tasks_completed=5"},
    {"day": 4, "name": "Scrolling & Navigation Assessment", "type": "scroll",
     "duration": 20, "criteria": "pages_viewed=3"},
    {"day": 5, "name": "Mixed Productivity Assessment", "type": "mixed",
     "duration": 35, "criteria": "activities_completed=4"},
    {"day": 6, "name": "Free Usage Observation", "type": "free",
     "duration": 90, "criteria": "observation_minutes=60"},
    {"day": 7, "name": "Final Validation & Training", "type": "final",
     "duration": 30, "criteria": "model_trained=true"},
]


class AssignmentManager:
    """Creates and tracks daily enrollment assignments."""

    def __init__(self, db: SQLiteManager) -> None:
        self._db = db

    def generate_all(self, user_id: str) -> list[str]:
        """Generate all 7 daily assignments.

        Args:
            user_id: User to generate assignments for

        Returns:
            List of assignment IDs
        """
        assignment_ids = []
        for da in DAILY_ASSIGNMENTS:
            aid = str(uuid.uuid4())
            self._db.execute(
                """INSERT INTO assignments 
                (assignment_id, assignment_name, day_number, duration_minutes, 
                 assignment_type, completion_criteria)
                VALUES (?, ?, ?, ?, ?, ?)""",
                (aid, da["name"], da["day"], da["duration"],
                 da["type"], da["criteria"]),
            )
            assignment_ids.append(aid)
        return assignment_ids

    def get_today_assignment(self, day: int) -> Optional[dict[str, Any]]:
        """Get the assignment for a specific day.

        Args:
            day: Day number (1-7)

        Returns:
            Assignment dict or None
        """
        row = self._db.fetch_one(
            "SELECT * FROM assignments WHERE day_number = ?", (day,)
        )
        return row

    def complete_assignment(self, assignment_id: str) -> bool:
        """Mark an assignment as completed.

        Args:
            assignment_id: Assignment to complete

        Returns:
            True if completed
        """
        try:
            self._db.execute(
                """INSERT INTO assignment_progress 
                (assignment_id, completion_time, completion_percentage, validation_status)
                VALUES (?, datetime('now'), 100.0, 'completed')""",
                (assignment_id,),
            )
            return True
        except Exception as e:
            logger.error(f"Failed to complete assignment: {e}")
            return False

    def get_all_assignments(self) -> list[dict[str, Any]]:
        """Get all assignments with progress."""
        return self._db.fetch_all(
            """SELECT a.*, ap.completion_percentage, ap.validation_status
            FROM assignments a
            LEFT JOIN assignment_progress ap ON a.assignment_id = ap.assignment_id
            ORDER BY a.day_number"""
        )

"""Cleanup Manager - Removes unnecessary data to maintain storage efficiency."""

import logging
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional

from src.data.sqlite_manager import SQLiteManager
from src.utils.constants import TEMP_DIR, LOGS_DIR

logger = logging.getLogger(__name__)


class CleanupManager:
    """Manages cleanup of obsolete application data."""

    def __init__(self, db: SQLiteManager) -> None:
        self._db = db

    def cleanup_temp_files(self) -> int:
        """Remove temporary files.

        Returns:
            Number of files removed
        """
        removed = 0
        try:
            if TEMP_DIR.exists():
                for f in TEMP_DIR.iterdir():
                    if f.is_file():
                        f.unlink()
                        removed += 1
            if removed > 0:
                logger.debug(f"Removed {removed} temp file(s)")
        except Exception as e:
            logger.error(f"Temp cleanup failed: {e}")
        return removed

    def cleanup_old_logs(self, retention_days: int = 30) -> int:
        """Remove old log files.

        Args:
            retention_days: Retention period in days

        Returns:
            Number of log files removed
        """
        removed = 0
        cutoff = datetime.now() - timedelta(days=retention_days)
        try:
            for log_file in LOGS_DIR.glob("*.log*"):
                if log_file.is_file():
                    mtime = datetime.fromtimestamp(log_file.stat().st_mtime)
                    if mtime < cutoff:
                        log_file.unlink()
                        removed += 1
        except Exception as e:
            logger.error(f"Log cleanup failed: {e}")
        return removed

    def cleanup_old_events(self, retention_hours: int = 1) -> int:
        """Remove raw behavioral events after processing.

        Args:
            retention_hours: Hours to retain raw events

        Returns:
            Number of events removed
        """
        cutoff = (datetime.now() - timedelta(hours=retention_hours)).isoformat()
        try:
            self._db.execute(
                "DELETE FROM behavioral_events WHERE timestamp < ?",
                (cutoff,),
            )
            affected = self._db._get_connection().total_changes
            if affected > 0:
                logger.debug(f"Cleaned {affected} old events")
            return affected
        except Exception as e:
            logger.error(f"Event cleanup failed: {e}")
            return 0

    def cleanup_old_auth_history(self, retention_days: int = 365) -> int:
        """Remove old authentication history.

        Args:
            retention_days: Retention period in days

        Returns:
            Number of records removed
        """
        cutoff = (datetime.now() - timedelta(days=retention_days)).isoformat()
        try:
            self._db.execute(
                "DELETE FROM authentication_history WHERE timestamp < ?",
                (cutoff,),
            )
            affected = self._db._get_connection().total_changes
            return affected
        except Exception as e:
            logger.error(f"Auth history cleanup failed: {e}")
            return 0

    def optimize_storage(self) -> dict[str, Any]:
        """Perform complete storage optimization.

        Returns:
            Dict with cleanup statistics
        """
        stats = {
            "temp_files_removed": self.cleanup_temp_files(),
            "old_events_removed": self.cleanup_old_events(),
            "logs_removed": self.cleanup_old_logs(),
        }

        # Vacuum database
        try:
            self._db.execute("VACUUM")
            stats["db_optimized"] = True
        except Exception as e:
            logger.warning(f"Database vacuum failed: {e}")
            stats["db_optimized"] = False

        # Record cleanup
        total_removed = sum(
            v for k, v in stats.items() if isinstance(v, int)
        )
        self._db.execute(
            """INSERT INTO cleanup_history (cleanup_date, records_removed, storage_freed)
            VALUES (datetime('now'), ?, 0)""",
            (total_removed,),
        )

        logger.info(f"Storage cleanup completed: {total_removed} items removed")
        return stats

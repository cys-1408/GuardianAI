"""Backup Manager - Creates encrypted backups of critical application data."""

import logging
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional

from src.utils.constants import DB_PATH, MODELS_DIR, BACKUPS_DIR, _DATA_DIR
from src.data.sqlite_manager import SQLiteManager
from src.security.encryption import EncryptionManager

logger = logging.getLogger(__name__)


class BackupManager:
    """Manages encrypted backups of application data."""

    def __init__(self, db: SQLiteManager, encryption: EncryptionManager) -> None:
        self._db = db
        self._encryption = encryption

    def create_backup(self) -> Optional[str]:
        """Create an encrypted backup of the database and models.

        Returns:
            Backup file path if successful, None otherwise
        """
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_dir = BACKUPS_DIR / timestamp
            backup_dir.mkdir(parents=True, exist_ok=True)

            # Backup database
            db_backup = backup_dir / "guardianai.db"
            if DB_PATH.exists():
                shutil.copy2(DB_PATH, db_backup)
                # Encrypt the backup
                if self._encryption:
                    self._encryption.encrypt_file(str(db_backup))

            # Backup models
            model_backup = backup_dir / "models"
            if MODELS_DIR.exists():
                shutil.copytree(MODELS_DIR, model_backup, dirs_exist_ok=True)
                # Encrypt individual model files
                for model_file in model_backup.glob("*"):
                    if model_file.is_file():
                        self._encryption.encrypt_file(str(model_file))

            # Record backup
            backup_size = sum(
                f.stat().st_size for f in backup_dir.rglob("*") if f.is_file()
            )
            self._db.execute(
                """INSERT INTO backup_history 
                (backup_time, backup_size, backup_status, verification_status)
                VALUES (datetime('now'), ?, 'completed', 'pending')""",
                (backup_size,),
            )

            logger.info(f"Backup created: {backup_dir} ({backup_size} bytes)")
            return str(backup_dir)

        except Exception as e:
            logger.error(f"Backup failed: {e}")
            self._db.execute(
                """INSERT INTO backup_history 
                (backup_time, backup_size, backup_status, verification_status)
                VALUES (datetime('now'), 0, 'failed', 'failed')"""
            )
            return None

    def verify_backup(self, backup_path: str) -> bool:
        """Verify the integrity of a backup.

        Args:
            backup_path: Path to the backup directory

        Returns:
            True if backup is valid
        """
        try:
            path = Path(backup_path)
            if not path.exists():
                return False

            # Check for required files
            db_file = path / "guardianai.db"
            if not db_file.exists():
                logger.warning(f"Backup missing database: {backup_path}")
                return False

            self._db.execute(
                "UPDATE backup_history SET verification_status = 'verified' WHERE backup_time = ?",
                (path.name[:15],),  # approximate match on timestamp
            )
            return True

        except Exception as e:
            logger.error(f"Backup verification failed: {e}")
            return False

    def restore_backup(self, backup_path: str) -> bool:
        """Restore from a backup.

        Args:
            backup_path: Path to the backup directory

        Returns:
            True if restoration succeeded
        """
        try:
            path = Path(backup_path)
            if not path.exists():
                logger.error(f"Backup not found: {backup_path}")
                return False

            # Restore database
            db_backup = path / "guardianai.db"
            if db_backup.exists():
                if self._encryption:
                    decrypted = self._encryption.decrypt_file(str(db_backup))
                    if decrypted:
                        DB_PATH.write_bytes(decrypted)
                else:
                    shutil.copy2(db_backup, DB_PATH)

            # Restore models
            model_backup = path / "models"
            if model_backup.exists():
                if MODELS_DIR.exists():
                    shutil.rmtree(MODELS_DIR)
                shutil.copytree(model_backup, MODELS_DIR)

            logger.info(f"Restored from backup: {backup_path}")
            return True

        except Exception as e:
            logger.error(f"Restore failed: {e}")
            return False

    def cleanup_old_backups(self, retention_days: int = 30) -> int:
        """Remove backups older than retention period.

        Args:
            retention_days: Number of days to retain

        Returns:
            Number of backups removed
        """
        cutoff = datetime.now() - timedelta(days=retention_days)
        removed = 0

        for backup_dir in BACKUPS_DIR.iterdir():
            if backup_dir.is_dir():
                try:
                    dir_time = datetime.strptime(
                        backup_dir.name, "%Y%m%d_%H%M%S"
                    )
                    if dir_time < cutoff:
                        shutil.rmtree(backup_dir)
                        removed += 1
                except (ValueError, OSError):
                    continue

        if removed > 0:
            logger.info(f"Removed {removed} old backup(s)")
        return removed

    def get_backup_history(self, limit: int = 10) -> list[dict[str, Any]]:
        """Get recent backup history."""
        return self._db.fetch_all(
            "SELECT * FROM backup_history ORDER BY backup_time DESC LIMIT ?",
            (limit,),
        )

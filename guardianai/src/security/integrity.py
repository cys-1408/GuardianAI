"""Integrity Manager - Ensures stored application resources have not been modified.

Verifies file integrity, detects tampering, validates database consistency,
and monitors model integrity using cryptographic hashing.
"""

import hashlib
import json
import logging
from pathlib import Path
from typing import Optional

from src.utils.constants import _DATA_DIR

logger = logging.getLogger(__name__)

_INTEGRITY_DB = _DATA_DIR / "integrity_checksums.json"


class IntegrityManager:
    """Manages integrity verification of application resources."""

    def __init__(self) -> None:
        self._checksums: dict[str, str] = {}
        self._load_checksums()

    def _load_checksums(self) -> None:
        """Load saved checksums from disk."""
        if _INTEGRITY_DB.exists():
            try:
                data = _INTEGRITY_DB.read_text()
                self._checksums = json.loads(data)
            except (json.JSONDecodeError, Exception) as e:
                logger.warning(f"Failed to load integrity database: {e}")
                self._checksums = {}

    def _save_checksums(self) -> None:
        """Persist checksums to disk."""
        try:
            _INTEGRITY_DB.write_text(json.dumps(self._checksums, indent=2))
        except Exception as e:
            logger.error(f"Failed to save integrity database: {e}")

    def _compute_hash(self, file_path: Path) -> Optional[str]:
        """Compute SHA-256 hash of a file.

        Args:
            file_path: Path to the file

        Returns:
            Hex digest string or None on failure
        """
        try:
            sha256 = hashlib.sha256()
            with open(file_path, 'rb') as f:
                for chunk in iter(lambda: f.read(65536), b''):
                    sha256.update(chunk)
            return sha256.hexdigest()
        except (IOError, OSError) as e:
            logger.error(f"Failed to compute hash for {file_path}: {e}")
            return None

    def register_file(self, file_path: str) -> bool:
        """Register a file for integrity monitoring.

        Args:
            file_path: Path to the file

        Returns:
            True if registration succeeded
        """
        path = Path(file_path)
        if not path.exists():
            logger.error(f"Cannot register non-existent file: {file_path}")
            return False

        hash_val = self._compute_hash(path)
        if hash_val:
            self._checksums[str(path)] = hash_val
            self._save_checksums()
            logger.debug(f"Registered file: {file_path}")
            return True
        return False

    def verify_file(self, file_path: str) -> bool:
        """Verify integrity of a registered file.

        Args:
            file_path: Path to the file

        Returns:
            True if integrity check passed
        """
        path = Path(file_path)
        if str(path) not in self._checksums:
            logger.warning(f"File not registered for integrity: {file_path}")
            return False

        stored_hash = self._checksums[str(path)]
        current_hash = self._compute_hash(path)

        if not current_hash:
            return False

        if current_hash != stored_hash:
            logger.error(f"Integrity check FAILED for {file_path}")
            return False

        logger.debug(f"Integrity check passed: {file_path}")
        return True

    def verify_all(self) -> dict[str, bool]:
        """Verify integrity of all registered files.

        Returns:
            Dict mapping file paths to verification results
        """
        results = {}
        for file_path in list(self._checksums.keys()):
            results[file_path] = self.verify_file(file_path)
        return results

    def get_integrity_report(self) -> dict:
        """Generate a full integrity report."""
        results = self.verify_all()
        total = len(results)
        passed = sum(1 for v in results.values() if v)
        return {
            "total_files": total,
            "passed": passed,
            "failed": total - passed,
            "details": results,
            "checksum_db_size": len(self._checksums),
        }

    def clear_checksums(self) -> None:
        """Clear all stored checksums."""
        self._checksums.clear()
        self._save_checksums()
        logger.info("Integrity checksums cleared")

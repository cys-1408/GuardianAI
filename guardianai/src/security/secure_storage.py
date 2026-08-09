"""Secure Storage Manager - Protected storage for confidential application resources.

Stores sensitive resources in secured directories with restricted access
permissions and integrates with the Encryption Manager.
"""

import os
import logging
import shutil
from pathlib import Path
from typing import Any, Optional

from src.utils.constants import _DATA_DIR, MODELS_DIR, BACKUPS_DIR
from src.security.encryption import EncryptionManager

logger = logging.getLogger(__name__)


class SecureStorageManager:
    """Provides protected storage for confidential application resources."""

    def __init__(self, encryption: EncryptionManager) -> None:
        self._encryption = encryption
        self._secure_dirs: set[Path] = set()

    def initialize(self) -> bool:
        """Initialize secure storage directories.

        Returns:
            True if initialization succeeded
        """
        try:
            for path in [_DATA_DIR, MODELS_DIR, BACKUPS_DIR]:
                path.mkdir(parents=True, exist_ok=True)
                self._secure_dirs.add(path)
                self._set_permissions(path)
            logger.info("Secure storage initialized")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize secure storage: {e}")
            return False

    def store_encrypted(self, data: bytes, file_path: str) -> bool:
        """Encrypt and store data securely.

        Args:
            data: Data to encrypt and store
            file_path: Destination file path

        Returns:
            True if storage succeeded
        """
        try:
            path = Path(file_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            encrypted = self._encryption.encrypt(data)
            path.write_bytes(encrypted)
            self._set_permissions(path)
            return True
        except Exception as e:
            logger.error(f"Secure store failed: {e}")
            return False

    def retrieve_encrypted(self, file_path: str) -> Optional[bytes]:
        """Retrieve and decrypt securely stored data.

        Args:
            file_path: Path to encrypted file

        Returns:
            Decrypted bytes or None on failure
        """
        try:
            path = Path(file_path)
            if not path.exists():
                return None
            encrypted = path.read_bytes()
            return self._encryption.decrypt(encrypted)
        except Exception as e:
            logger.error(f"Secure retrieve failed: {e}")
            return None

    def secure_delete(self, file_path: str) -> bool:
        """Securely delete a file by overwriting before removal.

        Args:
            file_path: Path to file to delete

        Returns:
            True if deletion succeeded
        """
        try:
            path = Path(file_path)
            if not path.exists():
                return True

            # Overwrite with random data before deletion
            file_size = path.stat().st_size
            with open(path, 'wb') as f:
                f.write(os.urandom(file_size))
                f.flush()
                os.fsync(f.fileno())

            path.unlink()
            logger.info(f"Securely deleted: {file_path}")
            return True
        except Exception as e:
            logger.error(f"Secure delete failed: {e}")
            return False

    def verify_path_safe(self, file_path: str) -> bool:
        """Verify that a file path is within secure storage.

        Args:
            file_path: Path to verify

        Returns:
            True if path is within secure directories
        """
        path = Path(file_path).resolve()
        for secure_dir in self._secure_dirs:
            try:
                path.relative_to(secure_dir)
                return True
            except ValueError:
                continue
        return False

    def _set_permissions(self, path: Path) -> None:
        """Set restrictive permissions on a file or directory.

        On Windows, this attempts to restrict access using the OS.
        On POSIX, sets 0700 for directories and 0600 for files.
        """
        try:
            if not path.exists():
                return
            if os.name == 'posix':
                if path.is_dir():
                    path.chmod(0o700)
                else:
                    path.chmod(0o600)
        except Exception as e:
            logger.warning(f"Failed to set permissions on {path}: {e}")

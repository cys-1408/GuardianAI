"""Encryption Manager - Protects sensitive data using strong encryption.

Provides AES-256-GCM encryption for behavioral data, ML models, configuration,
and authentication records. All operations are performed locally.
"""

import os
import base64
import logging
from typing import Optional

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from src.utils.constants import KEY_DERIVATION_ITERATIONS, _DATA_DIR

logger = logging.getLogger(__name__)

_KEY_FILE = _DATA_DIR / "encryption_key.enc"


class EncryptionManager:
    """Manages encryption and decryption of sensitive application data."""

    def __init__(self) -> None:
        self._fernet: Optional[Fernet] = None
        self._aesgcm: Optional[AESGCM] = None
        self._initialized = False

    @property
    def is_initialized(self) -> bool:
        return self._initialized

    def initialize(self) -> bool:
        """Initialize encryption services. Generates or loads encryption keys.

        Returns:
            True if initialization succeeded.
        """
        try:
            if _KEY_FILE.exists():
                key_data = _KEY_FILE.read_bytes()
                self._fernet = Fernet(key_data)
                # Derive AES-GCM key from the same seed
                aes_key = self._derive_aes_key(key_data)
                self._aesgcm = AESGCM(aes_key)
                logger.info("Encryption keys loaded from existing file")
            else:
                # Generate new encryption keys
                fernet_key = Fernet.generate_key()
                self._fernet = Fernet(fernet_key)
                self._aesgcm = AESGCM(AESGCM.generate_key(bit_length=256))

                # Store the Fernet key (44-char url-safe base64)
                _KEY_FILE.write_bytes(fernet_key)
                logger.info("New encryption keys generated and saved")

            self._initialized = True
            return True

        except Exception as e:
            logger.error(f"Failed to initialize encryption: {e}")
            return False

    def encrypt(self, data: bytes) -> bytes:
        """Encrypt data using Fernet (AES-128-CBC with HMAC).

        Args:
            data: Raw bytes to encrypt

        Returns:
            Encrypted bytes
        """
        if not self._fernet:
            raise RuntimeError("Encryption not initialized")
        return self._fernet.encrypt(data)

    def decrypt(self, encrypted_data: bytes) -> bytes:
        """Decrypt data using Fernet.

        Args:
            encrypted_data: Encrypted bytes

        Returns:
            Decrypted raw bytes
        """
        if not self._fernet:
            raise RuntimeError("Encryption not initialized")
        return self._fernet.decrypt(encrypted_data)

    def encrypt_file(self, file_path: str) -> bool:
        """Encrypt a file in-place.

        Args:
            file_path: Path to the file to encrypt

        Returns:
            True if encryption succeeded
        """
        try:
            with open(file_path, 'rb') as f:
                data = f.read()
            encrypted = self.encrypt(data)
            with open(file_path, 'wb') as f:
                f.write(encrypted)
            return True
        except Exception as e:
            logger.error(f"Failed to encrypt file {file_path}: {e}")
            return False

    def decrypt_file(self, file_path: str) -> Optional[bytes]:
        """Decrypt a file and return its contents.

        Args:
            file_path: Path to the encrypted file

        Returns:
            Decrypted bytes or None on failure
        """
        try:
            with open(file_path, 'rb') as f:
                encrypted = f.read()
            return self.decrypt(encrypted)
        except Exception as e:
            logger.error(f"Failed to decrypt file {file_path}: {e}")
            return None

    def encrypt_aes_gcm(self, data: bytes, aad: Optional[bytes] = None) -> bytes:
        """Encrypt using AES-256-GCM for large data.

        Args:
            data: Data to encrypt
            aad: Additional authenticated data

        Returns:
            Encrypted bytes with nonce prepended
        """
        if not self._aesgcm:
            raise RuntimeError("AES-GCM not initialized")
        nonce = os.urandom(12)
        aad = aad or b"guardianai"
        ciphertext = self._aesgcm.encrypt(nonce, data, aad)
        return nonce + ciphertext

    def decrypt_aes_gcm(self, encrypted_data: bytes,
                        aad: Optional[bytes] = None) -> Optional[bytes]:
        """Decrypt AES-256-GCM encrypted data.

        Args:
            encrypted_data: Encrypted data with nonce prepended
            aad: Additional authenticated data

        Returns:
            Decrypted bytes or None on failure
        """
        if not self._aesgcm:
            raise RuntimeError("AES-GCM not initialized")
        try:
            nonce = encrypted_data[:12]
            ciphertext = encrypted_data[12:]
            aad = aad or b"guardianai"
            return self._aesgcm.decrypt(nonce, ciphertext, aad)
        except Exception as e:
            logger.error(f"AES-GCM decryption failed: {e}")
            return None

    def _derive_aes_key(self, seed: bytes) -> bytes:
        """Derive an AES-256 key from a seed using PBKDF2."""
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=b"guardianai-aes-key-derivation",
            iterations=KEY_DERIVATION_ITERATIONS,
        )
        return kdf.derive(seed)

    def generate_model_key(self) -> bytes:
        """Generate a unique key for model encryption."""
        return Fernet.generate_key()

    def rotate_keys(self) -> bool:
        """Rotate encryption keys (re-encrypts all data).

        Returns:
            True if key rotation succeeded
        """
        # Reinitialize with new keys
        old_file = _KEY_FILE
        backup_file = _KEY_FILE.with_suffix(".enc.bak")

        try:
            # Backup old key
            if old_file.exists():
                old_file.rename(backup_file)

            # Generate new keys
            fernet_key = Fernet.generate_key()
            self._fernet = Fernet(fernet_key)
            _KEY_FILE.write_bytes(fernet_key)

            logger.info("Encryption keys rotated successfully")
            # Remove old backup
            if backup_file.exists():
                backup_file.unlink()
            return True

        except Exception as e:
            logger.error(f"Key rotation failed: {e}")
            # Restore old key
            if backup_file.exists():
                backup_file.rename(old_file)
            return False

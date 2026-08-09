"""Tests for encryption and secure storage."""

import os
import pytest
import tempfile
from pathlib import Path

from src.security.encryption import EncryptionManager


@pytest.fixture
def encryption():
    """Create an EncryptionManager instance with temp key storage."""
    old = os.environ.get('GUARDIANAI_DATA_DIR')
    tmpdir = tempfile.mkdtemp()
    os.environ['GUARDIANAI_DATA_DIR'] = tmpdir
    
    import src.utils.constants as C
    C._DATA_DIR = Path(tmpdir)
    # Patch the encryption module's module-level _KEY_FILE to use temp dir
    import src.security.encryption as enc_mod
    enc_mod._KEY_FILE = Path(tmpdir) / "encryption_key.enc"
    
    em = EncryptionManager()
    em.initialize()
    yield em
    
    if old:
        os.environ['GUARDIANAI_DATA_DIR'] = old
    else:
        del os.environ['GUARDIANAI_DATA_DIR']


class TestEncryptionManager:
    def test_initialize(self, encryption):
        assert encryption.is_initialized
    
    def test_encrypt_decrypt_fernet(self, encryption):
        data = b"Sensitive behavioral data"
        encrypted = encryption.encrypt(data)
        assert encrypted != data
        decrypted = encryption.decrypt(encrypted)
        assert decrypted == data
    
    def test_encrypt_decrypt_aes_gcm(self, encryption):
        data = b"Large feature vector data" * 100
        encrypted = encryption.encrypt_aes_gcm(data)
        assert encrypted != data
        decrypted = encryption.decrypt_aes_gcm(encrypted)
        assert decrypted == data
    
    def test_encrypt_file(self, encryption, tmp_path):
        test_file = tmp_path / "test.dat"
        test_file.write_bytes(b"Test model data")
        assert encryption.encrypt_file(str(test_file))
        
        encrypted = test_file.read_bytes()
        assert encrypted != b"Test model data"
        
        decrypted = encryption.decrypt_file(str(test_file))
        assert decrypted == b"Test model data"
    
    def test_generate_model_key(self, encryption):
        key = encryption.generate_model_key()
        assert len(key) > 0
    
    def test_key_rotation(self, encryption):
        # Key rotation generates a new key; old ciphertexts cannot be decrypted
        # (the old key is securely discarded per security best practices)
        data = b"Pre-rotation data"
        encrypted = encryption.encrypt(data)
        assert encryption.rotate_keys()
        # New key should be able to encrypt/decrypt fresh data
        new_data = b"Post-rotation data"
        new_encrypted = encryption.encrypt(new_data)
        assert encryption.decrypt(new_encrypted) == new_data
        # But old encrypted data is no longer decryptable (key was rotated)
        import pytest
        from cryptography.fernet import InvalidToken
        with pytest.raises((RuntimeError, InvalidToken)):
            encryption.decrypt(encrypted)

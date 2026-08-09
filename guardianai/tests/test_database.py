"""Tests for SQLiteManager and data repositories."""

import os
import pytest
import tempfile
import threading
from pathlib import Path

from src.data.sqlite_manager import SQLiteManager, DatabaseError
from src.data.behavioral_repo import BehavioralRepository
from src.data.feature_repo import FeatureRepository
from src.data.audit_repo import AuditRepository
from src.data.sliding_window import SlidingWindowManager
from src.utils.signals import FeatureVector
from datetime import datetime


@pytest.fixture
def temp_db():
    """Create a temporary SQLite database for testing."""
    old_path = os.environ.get('GUARDIANAI_DATA_DIR')
    
    # Force-reset SQLiteManager singleton for test isolation
    SQLiteManager._instance = None
    SQLiteManager._instance_lock = threading.Lock()
    
    tmpdir = tempfile.mkdtemp()
    os.environ['GUARDIANAI_DATA_DIR'] = tmpdir
    
    import src.utils.constants as C
    C.DB_PATH = Path(tmpdir) / "test.db"
    
    db = SQLiteManager()
    # Override the DB path directly since the singleton was created from
    # import-time constants that the env-var override doesn't reach
    test_db_path = Path(tmpdir) / "test.db"
    db._db_path = test_db_path
    db.initialize()
    yield db
    
    # Cleanup: clear singleton again so other tests get fresh state
    SQLiteManager._instance = None
    SQLiteManager._instance_lock = threading.Lock()
    SQLiteManager._instance_lock = threading.Lock()
    
    if old_path:
        os.environ['GUARDIANAI_DATA_DIR'] = old_path
    else:
        del os.environ['GUARDIANAI_DATA_DIR']


class TestSQLiteManager:
    def test_initialize(self, temp_db):
        assert temp_db.is_initialized
    
    def test_insert_and_fetch(self, temp_db):
        uid = temp_db.insert(
            "INSERT INTO users (user_id, full_name, registration_date, enrollment_status) VALUES (?, ?, datetime('now'), ?)",
            ("test_user", "Test User", "completed")
        )
        assert uid > 0
        
        row = temp_db.fetch_one("SELECT * FROM users WHERE user_id = ?", ("test_user",))
        assert row is not None
        assert row["full_name"] == "Test User"
    
    def test_fetch_all(self, temp_db):
        temp_db.execute("INSERT INTO users (user_id, full_name, registration_date) VALUES (?, ?, datetime('now'))", ("u1", "User 1"))
        temp_db.execute("INSERT INTO users (user_id, full_name, registration_date) VALUES (?, ?, datetime('now'))", ("u2", "User 2"))
        rows = temp_db.fetch_all("SELECT * FROM users")
        # The singleton may contain data from prior test_insert_and_fetch;
        # assert at least our two inserts are present
        user_ids = [r["user_id"] for r in rows]
        assert "u1" in user_ids
        assert "u2" in user_ids
        assert len(rows) >= 2
    
    def test_transaction(self, temp_db):
        def insert_users():
            temp_db.execute("INSERT INTO users (user_id, full_name, registration_date) VALUES (?, ?, datetime('now'))", ("tx1", "Tx 1"))
            temp_db.execute("INSERT INTO users (user_id, full_name, registration_date) VALUES (?, ?, datetime('now'))", ("tx2", "Tx 2"))
            return "done"
        
        result = temp_db.transaction(insert_users)
        assert result == "done"
        assert temp_db.fetch_one("SELECT * FROM users WHERE user_id = 'tx1'") is not None


class TestBehavioralRepository:
    def _create_test_session(self, db, user_id="test_user_beh") -> str:
        """Helper to insert a user + session for foreign key compliance."""
        db.execute(
            "INSERT OR IGNORE INTO users (user_id, full_name, registration_date) VALUES (?, ?, datetime('now'))",
            (user_id, "Test User"),
        )
        db.execute(
            "INSERT OR IGNORE INTO sessions (session_id, user_id, start_time) VALUES (?, ?, datetime('now'))",
            ("s1", user_id),
        )
        return "s1"

    def test_store_and_retrieve(self, temp_db):
        self._create_test_session(temp_db)
        repo = BehavioralRepository(temp_db)
        fv = FeatureVector(features=[0.1, 0.2, 0.3], timestamp=datetime.now(), session_id="s1")
        fid = repo.store_feature(fv, "high")
        assert fid is not None
        
        row = repo.get_feature(fid)
        assert row is not None
        assert row["trust_level"] == "high"
    
    def test_trusted_features(self, temp_db):
        self._create_test_session(temp_db)
        repo = BehavioralRepository(temp_db)
        fv = FeatureVector(features=[0.5], timestamp=datetime.now(), session_id="s1")
        fid = repo.store_feature(fv)
        assert repo.mark_trusted(fid, 0.9) == True


class TestAuditRepository:
    def test_record_event(self, temp_db):
        repo = AuditRepository(temp_db)
        log_id = repo.record_event("test_component", "warning", "Test warning", {"key": "val"})
        assert log_id > 0
    
    def test_auth_stats(self, temp_db):
        repo = AuditRepository(temp_db)
        stats = repo.get_auth_stats()
        assert "total_auths" in stats
        assert "trusted" in stats


class TestSlidingWindow:
    def test_window_stats(self, temp_db):
        behavior_repo = BehavioralRepository(temp_db)
        window = SlidingWindowManager(temp_db, behavior_repo)
        stats = window.get_window_stats()
        assert "total_trusted" in stats
        assert "pending_retraining" in stats

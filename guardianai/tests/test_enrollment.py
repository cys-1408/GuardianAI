"""Tests for Enrollment System."""

import os
import pytest
import tempfile
from pathlib import Path

from src.enrollment.assignments import AssignmentManager, DAILY_ASSIGNMENTS
from src.enrollment.progress import ProgressManager
from src.enrollment.validator import EnrollmentValidator


@pytest.fixture
def temp_db():
    """Create a temporary SQLite database for testing."""
    import src.utils.constants as C
    old = os.environ.get('GUARDIANAI_DATA_DIR')
    tmpdir = tempfile.mkdtemp()
    os.environ['GUARDIANAI_DATA_DIR'] = tmpdir
    
    from src.data.sqlite_manager import SQLiteManager
    import threading
    # Force-reset singleton for test isolation
    SQLiteManager._instance = None
    SQLiteManager._instance_lock = threading.Lock()
    
    test_db_path = Path(tmpdir) / "test.db"
    db = SQLiteManager()
    db._db_path = test_db_path
    db.initialize()
    yield db
    
    SQLiteManager._instance = None
    SQLiteManager._instance_lock = threading.Lock()
    
    if old:
        os.environ['GUARDIANAI_DATA_DIR'] = old
    else:
        del os.environ['GUARDIANAI_DATA_DIR']


class TestAssignmentManager:
    def test_generate_all(self, temp_db):
        mgr = AssignmentManager(temp_db)
        ids = mgr.generate_all("test_user")
        assert len(ids) == 7

    def test_get_today_assignment(self, temp_db):
        mgr = AssignmentManager(temp_db)
        mgr.generate_all("test_user")
        assignment = mgr.get_today_assignment(1)
        assert assignment is not None
        assert assignment["day_number"] == 1

    def test_get_all_assignments(self, temp_db):
        mgr = AssignmentManager(temp_db)
        mgr.generate_all("test_user")
        all_assignments = mgr.get_all_assignments()
        assert len(all_assignments) == 7

    def test_complete_assignment(self, temp_db):
        mgr = AssignmentManager(temp_db)
        ids = mgr.generate_all("test_user")
        assert mgr.complete_assignment(ids[0]) == True

    def test_daily_assignments_defined(self):
        assert len(DAILY_ASSIGNMENTS) == 7
        for day in range(1, 8):
            assert any(a["day"] == day for a in DAILY_ASSIGNMENTS)


class TestProgressManager:
    def test_initial_progress(self, temp_db):
        mgr = ProgressManager(temp_db)
        assert mgr.calculate() == 0.0

    def test_days_remaining_initial(self, temp_db):
        mgr = ProgressManager(temp_db)
        assert mgr.get_days_remaining() == 7


class TestEnrollmentValidator:
    def test_initial_validation(self, temp_db):
        validator = EnrollmentValidator(temp_db)
        assert validator.validate() == False  # No data yet

    def test_validation_report(self, temp_db):
        validator = EnrollmentValidator(temp_db)
        report = validator.get_report()
        assert "assignments_completed" in report
        assert "minimum_features" in report
        assert "feature_diversity" in report

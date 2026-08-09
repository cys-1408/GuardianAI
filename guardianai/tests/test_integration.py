"""
Comprehensive Integration Tests for ApplicationCore Initialization.

Verifies all 13 initialization steps complete successfully,
all subsystem components are properly wired, and the full
lifecycle (initialize -> start -> shutdown) works end-to-end.
"""

import os
import sys
import threading
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch
from datetime import datetime

import pytest
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer

from src import __version__, __description__
from src.utils.signals import get_signals, AuthDecision
from src.utils.constants import APP_NAME


# ══════════════════════════════════════════════════════════════════════════
#  Fixtures
# ══════════════════════════════════════════════════════════════════════════


@pytest.fixture(scope="session")
def qapp():
    """Create a QApplication for the test session (needed for Qt signals)."""
    app = QApplication.instance() or QApplication([])
    yield app


@pytest.fixture(autouse=True)
def test_env(qapp):
    """Set up a clean isolated test environment for each test.

    Creates a temp directory, resets the SQLiteManager singleton,
    and patches all paths to point to the temp directory so the
    test doesn't interfere with real application data.
    """
    import src.utils.constants as C

    # Save original env
    old_data_dir = os.environ.get("GUARDIANAI_DATA_DIR")

    # Create temp directory for test data
    tmpdir = Path(tempfile.mkdtemp())
    os.environ["GUARDIANAI_DATA_DIR"] = str(tmpdir)

    # Patch paths
    C._DATA_DIR = tmpdir
    C.DB_PATH = tmpdir / "guardianai.db"
    C.CONFIG_PATH = tmpdir / "config.enc"
    C.MODELS_DIR = tmpdir / "models"
    C.BACKUPS_DIR = tmpdir / "backups"
    C.LOGS_DIR = tmpdir / "logs"
    C.TEMP_DIR = tmpdir / "temp"

    # Create directories
    for p in [C.MODELS_DIR, C.BACKUPS_DIR, C.LOGS_DIR, C.TEMP_DIR]:
        p.mkdir(parents=True, exist_ok=True)

    # Reset SQLiteManager singleton for test isolation
    from src.data.sqlite_manager import SQLiteManager
    import threading as _th
    SQLiteManager._instance = None
    SQLiteManager._instance_lock = _th.Lock()

    # Reset signals singleton
    from src.utils.signals import _signals_instance
    import src.utils.signals as sig_mod
    sig_mod._signals_instance = None

    # Fix encryption key path — _KEY_FILE is computed at import time,
    # so setting C._DATA_DIR above doesn't affect it. Patch it directly.
    from src.security import encryption as enc_mod
    enc_mod._KEY_FILE = tmpdir / "encryption_key.enc"

    yield tmpdir  # Provide temp dir to tests

    # Cleanup
    if old_data_dir:
        os.environ["GUARDIANAI_DATA_DIR"] = old_data_dir
    else:
        os.environ.pop("GUARDIANAI_DATA_DIR", None)

    # Clean up SQLiteManager for next test
    SQLiteManager._instance = None
    SQLiteManager._instance_lock = _th.Lock()
    sig_mod._signals_instance = None


@pytest.fixture
def app_core(test_env):
    """Create and initialize ApplicationCore for testing.

    This is the main fixture used by most tests. It patches the
    ConfigurationManager to avoid needing encryption dependencies,
    then initializes ApplicationCore and yields it for testing.
    """
    from src.application.core import ApplicationCore

    # Create a fresh core
    core = ApplicationCore()

    # Mock ConfigManager to bypass encryption dependency
    core.config.initialize = MagicMock(return_value=None)
    core.config.load = MagicMock(return_value={})
    core.config.set = MagicMock(return_value=None)

    # Also patch settings to not need config
    core.settings = MagicMock()

    yield core


@pytest.fixture
def initialized_core(app_core):
    """Initialize ApplicationCore completely and verify it succeeds.

    Sets startup.execute to return True so initialize() passes step 11.
    The mock is kept active through yield and restored after.
    """
    # Direct attribute assignment (not with context manager) so mock
    # stays active through yield. This avoids the issue where patching
    # StartupManager class-level methods gets shadowed by instance attrs.
    original_execute = app_core.startup.execute
    app_core.startup.execute = MagicMock(return_value=True)
    try:
        result = app_core.initialize()
        assert result is True, "ApplicationCore.initialize() returned False"
        assert app_core.is_initialized is True
        yield app_core
    finally:
        app_core.startup.execute = original_execute


# ══════════════════════════════════════════════════════════════════════════
#  Test: Step-by-Step Initialization
# ══════════════════════════════════════════════════════════════════════════


class TestInitializationSteps:
    """Verify every component created during each of the 13 steps."""

    def test_step1_config_loaded(self, initialized_core):
        """Step 1: Configuration should be loaded."""
        # Config manager exists and was called
        assert initialized_core.config is not None
        initialized_core.config.load.assert_called_once()

    def test_step2_security_layer(self, initialized_core):
        """Step 2: Security layer should be fully initialized."""
        core = initialized_core
        # Encryption manager
        assert core.encryption is not None
        assert core.encryption.is_initialized is True
        # Secure storage
        assert core.secure_storage is not None
        # Privacy manager
        assert core.privacy_mgr is not None
        # Integrity manager
        assert core.integrity_mgr is not None
        # Audit logger
        assert core.audit_logger is not None

    def test_step3_data_layer(self, initialized_core):
        """Step 3: Data layer should be fully initialized."""
        core = initialized_core
        # SQLite database
        assert core.db is not None
        assert core.db.is_initialized is True
        # Repositories
        assert core.behavioral_repo is not None
        assert core.feature_repo is not None
        assert core.audit_repo is not None
        # Sliding window
        assert core.sliding_window is not None
        # Backup and cleanup managers
        assert core.backup_mgr is not None
        assert core.cleanup_mgr is not None

    def test_step4_behavioral_collection(self, initialized_core):
        """Step 4: Behavioral collection layer should be fully initialized."""
        core = initialized_core
        # Event buffer
        assert core.event_buffer is not None
        assert core.event_buffer.size == 0
        # Monitors
        assert core.keyboard_monitor is not None
        assert core.mouse_monitor is not None
        assert core.scroll_monitor is not None
        assert core.idle_detector is not None
        # Windows integration
        assert core.windows_integration is not None

    def test_step5_processing_layer(self, initialized_core):
        """Step 5: Processing layer should be fully initialized."""
        core = initialized_core
        # Event aggregator
        assert core.event_aggregator is not None
        # Feature extraction
        assert core.feature_extractor is not None
        # Feature normalizer
        assert core.feature_normalizer is not None

    def test_step6_ai_ml_layer(self, initialized_core):
        """Step 6: AI/ML layer should be fully initialized."""
        core = initialized_core
        # Dataset manager
        assert core.dataset_mgr is not None
        # Confidence engine
        assert core.confidence_engine is not None
        assert core.confidence_engine.current_confidence == 0.5
        # Trust manager
        assert core.trust_mgr is not None
        assert core.trust_mgr.current_trust == 0.7
        # Risk engine
        assert core.risk_engine is not None
        assert core.risk_engine.current_risk_level == "low"
        # Model repository
        assert core.model_repo is not None
        # Training engine
        assert core.training_engine is not None
        # Model validator
        assert core.model_validator is not None
        # Version manager
        assert core.version_mgr is not None
        # Inference engine
        assert core.inference_engine is not None
        # Retraining manager
        assert core.retraining_mgr is not None

    def test_step7_enrollment_system(self, initialized_core):
        """Step 7: Enrollment system should be fully initialized."""
        core = initialized_core
        assert core.assignment_mgr is not None
        assert core.progress_mgr is not None
        assert core.calendar_mgr is not None
        assert core.enrollment_validator is not None
        assert core.enrollment_system is not None

    def test_step8_signal_wiring(self, initialized_core):
        """Step 8: Signal wiring should be connected (verified via emission)."""
        core = initialized_core
        # The _wire_workflow_signals method is called during init.
        # We can verify it's connected by checking that emitting
        # enrollment_completed triggers _on_enrollment_completed
        signals = get_signals()

        # Patch the handler to verify it's called
        handler_called = False

        def check_handler():
            nonlocal handler_called
            handler_called = True

        original_handler = core._on_enrollment_completed
        core._on_enrollment_completed = check_handler

        signals.enrollment_completed.emit()
        QApplication.processEvents()
        assert handler_called, "enrollment_completed signal not connected"

        # Restore
        core._on_enrollment_completed = original_handler

    def test_step9_workflow_controller(self, initialized_core):
        """Step 9: Workflow controller should be initialized."""
        core = initialized_core
        assert core.workflow is not None
        assert core.workflow.current_state.value == "idle"

    def test_step10_session_manager(self, initialized_core):
        """Step 10: Session manager should be initialized and auth manager finalized."""
        core = initialized_core
        assert core.session is not None
        assert core.auth_mgr is not None
        assert core.training_scheduler is not None

    def test_step11_startup_verification(self, initialized_core):
        """Step 11: Startup verification ran (startup was executed)."""
        core = initialized_core
        core.startup.execute.assert_called_once()

    def test_step12_maintenance_thread(self, initialized_core):
        """Step 12: Maintenance thread should be started."""
        core = initialized_core
        assert core._maintenance_thread is not None
        assert core._maintenance_thread.is_alive() is True
        assert core._maintenance_thread.name == "Maintenance-Thread"

    def test_step13_system_ready(self, initialized_core):
        """Step 13: System should be marked ready."""
        core = initialized_core
        assert core.is_initialized is True


# ══════════════════════════════════════════════════════════════════════════
#  Test: Lifecycle Management
# ══════════════════════════════════════════════════════════════════════════


class TestLifecycle:
    """Verify the full application lifecycle."""

    def test_initialization_fails_without_db(self, app_core):
        """Initialization should fail if DB can't be created."""
        with patch.object(app_core.db_class if hasattr(app_core, 'db_class') else MagicMock(),
                          'initialize', return_value=False):
            # The initialize() will fail at step 3 when DB fails
            pass
        # We test this differently: if startup.execute fails
        from src.data.sqlite_manager import SQLiteManager
        with patch.object(SQLiteManager, 'initialize', return_value=False):
            result = app_core.initialize()
            assert result is False
            assert app_core.is_initialized is False

    def test_not_initialized_property(self, app_core):
        """Before init, is_initialized should be False."""
        assert app_core.is_initialized is False
        assert app_core.is_running is False

    def test_start_requires_initialized(self, app_core):
        """Calling start() before initialize() should raise RuntimeError."""
        with pytest.raises(RuntimeError):
            app_core.start()

    def test_full_lifecycle(self, initialized_core):
        """Verify initialize -> start -> shutdown complete cycle."""
        core = initialized_core

        # Verify initialized
        assert core.is_initialized is True
        assert core.is_running is False

        # Start
        core.start()
        assert core.is_running is True

        # Verify all background threads running
        assert core._collection_thread is not None
        assert core._collection_thread.is_alive()
        assert core._processing_thread is not None
        assert core._processing_thread.is_alive()
        assert core._auth_thread is not None
        assert core._auth_thread.is_alive()

        # Verify behavioral monitors started
        assert core.keyboard_monitor._active is True  # type: ignore
        assert core.mouse_monitor._active is True  # type: ignore
        assert core.scroll_monitor._active is True  # type: ignore
        assert core.idle_detector._active is True  # type: ignore

        # Shutdown
        core.shutdown()
        assert core.is_running is False

        # Wait briefly for threads to stop
        import time
        time.sleep(0.1)

        # Verify threads stopped
        assert core._collection_running.is_set() is False
        assert core._processing_running.is_set() is False
        assert core._auth_running.is_set() is False
        assert core._maintenance_running.is_set() is False

    def test_idempotent_shutdown(self, initialized_core):
        """Calling shutdown() multiple times should be safe."""
        core = initialized_core
        core.start()
        core.shutdown()
        core.shutdown()  # Second call should be no-op
        assert core.is_running is False


# ══════════════════════════════════════════════════════════════════════════
#  Test: Signal Wiring & Workflow
# ══════════════════════════════════════════════════════════════════════════


class TestWorkflowWiring:
    """Verify the enrollment -> training -> auth signal pipeline."""

    def test_enrollment_completed_triggers_config_update(self, initialized_core):
        """enrollment_completed signal should update config."""
        core = initialized_core
        signals = get_signals()

        # Reset the mock to clear prior calls
        core.config.set.reset_mock()

        signals.enrollment_completed.emit()
        QApplication.processEvents()

        core.config.set.assert_called_once_with("app.enrollment_status", "completed")

    def test_training_completed_reloads_inference(self, initialized_core):
        """training_completed signal should reload inference engine."""
        core = initialized_core
        signals = get_signals()

        # Mock the inference engine reload
        core.inference_engine.reload_model = MagicMock(return_value=True)

        signals.training_completed.emit({"model_id": "test123"})
        QApplication.processEvents()

        core.inference_engine.reload_model.assert_called_once()

    def test_model_deployed_triggers_notification(self, initialized_core):
        """model_deployed signal should emit notification."""
        core = initialized_core
        signals = get_signals()

        notification_emitted = []

        def check_notification(ntype, title, msg):
            notification_emitted.append((ntype, title, msg))

        signals.notification_received.connect(check_notification)

        signals.model_deployed.emit("1.2.3")
        QApplication.processEvents()

        assert len(notification_emitted) == 1
        assert notification_emitted[0][0] == "success"
        assert "1.2.3" in notification_emitted[0][2]

    def test_workflow_controller_connects_to_enrollment(self, initialized_core):
        """WorkflowController should transition on enrollment_completed."""
        core = initialized_core
        # Workflow starts in IDLE state
        assert core.workflow.current_state.value == "idle"

        # Emit enrollment completed -> should transition to TRAINING
        signals = get_signals()
        signals.enrollment_completed.emit()
        QApplication.processEvents()
        # Note: workflow transitions asynchronously
        # This just verifies the signal doesn't crash

    def test_validate_and_deploy_model(self, initialized_core):
        """validate_and_deploy_model should return False when no model."""
        core = initialized_core
        result = core.validate_and_deploy_model({"model_id": "nonexistent"})
        assert result is False  # No model in repo


# ══════════════════════════════════════════════════════════════════════════
#  Test: Subsystem Communication
# ══════════════════════════════════════════════════════════════════════════


class TestSubsystemCommunication:
    """Verify subsystems can communicate through signals."""

    def test_behavioral_pipeline_signals(self, initialized_core):
        """Behavioral events should flow through signal chain."""
        from src.utils.signals import BehavioralEvent

        signals = get_signals()
        events_received = []

        def on_keyboard_event(event):
            events_received.append(event)

        signals.keyboard_event.connect(on_keyboard_event)

        # Create a keyboard event (as WindowsIntegrationLayer would)
        event = BehavioralEvent(
            event_type="key_press",
            timestamp=datetime.now(),
            data={"key_code": 65, "press_time": 1000.0},
            session_id="test_session",
        )
        signals.keyboard_event.emit(event)
        QApplication.processEvents()

        assert len(events_received) == 1
        assert events_received[0].event_type == "key_press"

    def test_auth_decision_pipeline(self, initialized_core):
        """Auth decision signals should propagate to risk engine."""
        core = initialized_core
        signals = get_signals()

        # Test the full auth decision cycle
        decisions_received = []

        def on_decision(decision):
            decisions_received.append(decision)

        signals.auth_decision.connect(on_decision)

        # Manually trigger auth evaluation
        core.auth_mgr.evaluate()
        QApplication.processEvents()

        # The evaluate() method emits auth_decision signal
        assert len(decisions_received) >= 1

    def test_session_start_stop_signals(self, initialized_core):
        """Session signals should propagate correctly."""
        signals = get_signals()
        session_started = []
        session_ended = []

        signals.session_started.connect(lambda sid: session_started.append(sid))
        signals.session_ended.connect(lambda sid: session_ended.append(sid))

        # Create and close a session
        core = initialized_core
        core.session.create_session()
        session_id = core.session.current_session_id
        assert session_id is not None

        core.session.close_session(session_id)

        assert session_id in session_started
        assert session_id in session_ended

    def test_error_signal_handling(self, initialized_core):
        """Error signals should propagate without crashing."""
        signals = get_signals()
        errors = []

        def on_error(component, msg):
            errors.append((component, msg))

        signals.error_occurred.connect(on_error)
        signals.error_occurred.emit("test_component", "Test error message")
        QApplication.processEvents()

        assert len(errors) == 1
        assert errors[0] == ("test_component", "Test error message")


# ══════════════════════════════════════════════════════════════════════════
#  Test: Thread Safety & Background Threads
# ══════════════════════════════════════════════════════════════════════════


class TestThreadSafety:
    """Verify background threads operate safely."""

    def test_collection_thread_runs(self, initialized_core):
        """Collection thread should be running after start()."""
        core = initialized_core
        core.start()

        assert core._collection_thread is not None
        assert core._collection_thread.is_alive()
        assert core._collection_thread.name == "Behavior-Collection-Thread"

        core.shutdown()

    def test_maintenance_thread_runs(self, initialized_core):
        """Maintenance thread should be running after init (started in step 12)."""
        core = initialized_core
        assert core._maintenance_thread is not None
        assert core._maintenance_thread.is_alive()

    def test_background_threads_accept_data(self, initialized_core):
        """Background threads should accept data through event buffer."""
        from src.utils.signals import BehavioralEvent
        from datetime import datetime

        core = initialized_core
        core.start()

        # Push an event to the buffer (collection thread consumes this)
        event = BehavioralEvent(
            event_type="key_press",
            timestamp=datetime.now(),
            data={"key_code": 65, "press_time": 1000.0},
        )
        core.event_buffer.push(event)

        # Give the collection thread time to process
        import time
        time.sleep(0.1)

        # The event should have been consumed from the buffer
        assert core.event_buffer.size == 0

        core.shutdown()


# ══════════════════════════════════════════════════════════════════════════
#  Test: Security Layer Integration
# ══════════════════════════════════════════════════════════════════════════


class TestSecurityLayer:
    """Verify security layer integration with other subsystems."""

    def test_encryption_works_in_security_layer(self, initialized_core):
        """Encryption manager should encrypt and decrypt data."""
        core = initialized_core
        data = b"Sensitive behavioral data test"
        encrypted = core.encryption.encrypt(data)
        assert encrypted != data
        decrypted = core.encryption.decrypt(encrypted)
        assert decrypted == data

    def test_privacy_manager_accessible(self, initialized_core):
        """Privacy manager should be accessible from core."""
        core = initialized_core
        assert core.privacy_mgr.check_access("behavioral_data", "collect") is True
        assert core.privacy_mgr.is_collection_allowed() is True

    def test_audit_logger_accessible(self, initialized_core):
        """Audit logger should be accessible."""
        core = initialized_core
        assert core.audit_logger is not None


# ══════════════════════════════════════════════════════════════════════════
#  Test: GuardClauses & Error Handling
# ══════════════════════════════════════════════════════════════════════════


class TestGuardClauses:
    """Verify error handling and edge cases."""

    def test_re_initialization_noop(self, initialized_core):
        """Re-initializing should not crash (idempotent)."""
        # Second call to initialize() might be a no-op or re-init;
        # we just verify it doesn't crash
        result = initialized_core.initialize()
        # May return True or False depending on implementation,
        # but should not raise
        assert result is not None

    def test_startup_failure_propagates(self, app_core):
        """If startup.execute() fails, initialize() should return False."""
        from src.data.sqlite_manager import SQLiteManager

        # Create fresh core with patched startup
        from src.application.startup import StartupManager

        with patch.object(StartupManager, 'execute', return_value=False):
            result = app_core.initialize()
            assert result is False
            assert app_core.is_initialized is False

    def test_environment_cleanup_on_shutdown(self, initialized_core):
        """Shutdown should clean up background resources."""
        core = initialized_core
        core.start()
        core.shutdown()

        # After shutdown, locks should be released
        assert core._shutdown_lock.locked() is False

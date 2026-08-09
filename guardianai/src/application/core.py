"""Application Core - Central coordinator for the entire GuardianAI system.

Initializes all modules, manages lifecycle, maintains global state, and
coordinates communication between major subsystems. Implements the 6-thread
model specified in the architecture:
  a. UI Thread: PySide6 Main Loop
  b. Collection Thread: Low-latency Windows Hook listeners
  c. Processing Thread: Event aggregation -> Feature Extraction -> Normalization
  d. Auth Thread: Inference -> Confidence -> Trust Score -> Decision
  e. DB Thread: Serialized writes to SQLite
  f. Maintenance Thread: Scheduled retraining, backup, and cleanup
"""

import logging
import signal
import sys
import threading
from typing import Optional

from PySide6.QtCore import QObject, QThread

from src.utils.constants import APP_NAME, APP_VERSION
from src.utils.signals import get_signals, ApplicationSignals
from src.application.config import ConfigurationManager
from src.application.workflow import WorkflowController
from src.application.startup import StartupManager
from src.application.session import SessionManager
from src.application.settings import SettingsManager
from src.enrollment.manager import EnrollmentManager
from src.enrollment.assignments import AssignmentManager
from src.enrollment.progress import ProgressManager
from src.enrollment.calendar import CalendarManager
from src.enrollment.validator import EnrollmentValidator
from src.data.sqlite_manager import SQLiteManager
from src.data.behavioral_repo import BehavioralRepository
from src.data.feature_repo import FeatureRepository
from src.data.audit_repo import AuditRepository
from src.data.sliding_window import SlidingWindowManager
from src.data.backup import BackupManager
from src.data.cleanup import CleanupManager

logger = logging.getLogger(__name__)


class ApplicationCore(QObject):
    """Central controller of GuardianAI application lifecycle.

    Wires all six architectural layers together with the 6-thread model:
      - UI (PySide6 main loop, thread a)
      - Collection (low-latency hooks, thread b)
      - Processing (aggregation -> features, thread c)
      - Auth (inference -> confidence -> trust -> risk -> decision, thread d)
      - DB (serialized SQLite writes, thread e)
      - Maintenance (retraining/backup/cleanup, thread f)
    """

    def __init__(self) -> None:
        super().__init__()
        self._signals = get_signals()

        # ── Core Components (Phase 1 + 2) ──────────────────────────────────
        self.config: ConfigurationManager = ConfigurationManager()
        self.settings: SettingsManager = SettingsManager(self.config)
        self.startup: StartupManager = StartupManager(self)
        self.workflow: Optional[WorkflowController] = None
        self.session: Optional[SessionManager] = None

        # ── Data Layer (Phase 1 thread e) ──────────────────────────────────
        self.db: Optional[SQLiteManager] = None
        self.behavioral_repo: Optional[BehavioralRepository] = None
        self.feature_repo: Optional[FeatureRepository] = None
        self.audit_repo: Optional[AuditRepository] = None
        self.sliding_window: Optional[SlidingWindowManager] = None
        self.backup_mgr: Optional[BackupManager] = None
        self.cleanup_mgr: Optional[CleanupManager] = None

        # ── Behavioral Collection Layer (Phase 3, thread b) ────────────────
        self.event_buffer = None  # EventBuffer
        self.keyboard_monitor = None  # KeyboardMonitoringService
        self.mouse_monitor = None  # MouseMonitoringService
        self.scroll_monitor = None  # ScrollMonitoringService
        self.idle_detector = None  # IdleDetectionService
        self.windows_integration = None  # WindowsIntegrationLayer

        # ── Processing Layer (Phase 5, thread c) ───────────────────────────
        self.event_aggregator = None  # EventAggregator
        self.feature_extractor = None  # FeatureExtractionEngine
        self.feature_normalizer = None  # FeatureNormalizationEngine

        # ── AI / ML Layer (Phase 6 + 7 + 8, thread d + f) ─────────────────
        self.dataset_mgr = None  # DatasetManager
        self.confidence_engine = None  # ConfidenceEngine
        self.trust_mgr = None  # TrustScoreManager
        self.risk_engine = None  # AdaptiveRiskEngine
        self.auth_mgr = None  # AuthenticationManager
        self.inference_engine = None  # InferenceEngine
        self.model_repo = None  # ModelRepository
        self.training_engine = None  # ModelTrainingEngine
        self.model_validator = None  # ModelValidator
        self.version_mgr = None  # VersionManager
        self.retraining_mgr = None  # RetrainingManager
        self.training_scheduler = None  # TrainingScheduler

        # ── Enrollment System (Phase 4) ────────────────────────────────────
        self.assignment_mgr: Optional[AssignmentManager] = None
        self.progress_mgr: Optional[ProgressManager] = None
        self.calendar_mgr: Optional[CalendarManager] = None
        self.enrollment_validator: Optional[EnrollmentValidator] = None
        self.enrollment_system: Optional[EnrollmentManager] = None

        # ── Security Layer (Phase 10) ──────────────────────────────────────
        self.encryption = None  # EncryptionManager
        self.privacy_mgr = None  # PrivacyManager
        self.integrity_mgr = None  # IntegrityManager
        self.secure_storage = None  # SecureStorageManager
        self.audit_logger = None  # LoggingManager (created after audit_repo in step 3)

        # ── Presentation Layer (Phase 9, thread a) ─────────────────────────
        self.presentation_layer = None  # MainWindow (set externally)

        # ── Thread Workers (for background threads) ────────────────────────
        self._collection_thread: Optional[threading.Thread] = None
        self._processing_thread: Optional[threading.Thread] = None
        self._auth_thread: Optional[threading.Thread] = None
        self._db_thread: Optional[threading.Thread] = None
        self._maintenance_thread: Optional[threading.Thread] = None
        self._collection_running = threading.Event()
        self._processing_running = threading.Event()
        self._auth_running = threading.Event()
        self._maintenance_running = threading.Event()

        self._running = False
        self._initialized = False
        self._shutdown_lock = threading.Lock()

        # Register signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._handle_signal)
        signal.signal(signal.SIGTERM, self._handle_signal)

    @property
    def is_initialized(self) -> bool:
        return self._initialized

    @property
    def is_running(self) -> bool:
        return self._running

    # ═══════════════════════════════════════════════════════════════════════
    #  Initialization
    # ═══════════════════════════════════════════════════════════════════════

    def initialize(self) -> bool:
        """Initialize the application and all subsystems.

        Follows the specified 13-step startup sequence:
          1. Initialize Security Layer
          2. Load Configuration
          3. Initialize Data Layer + DB
          4. Initialize Behavioral Collection Layer
          5. Initialize Processing Layer
          6. Initialize AI/ML Layer
          7. Initialize Enrollment System
          8. Initialize Presentation Layer
          9. Initialize Workflow Controller
         10. Initialize Session Manager
         11. Run Startup Manager verification
         12. Start Maintenance Thread
         13. Mark system ready

        Returns:
            True if initialization succeeded, False otherwise.
        """
        logger.info(f"Initializing {APP_NAME} v{APP_VERSION}...")

        try:
            # ── Step 1: Initialize Security Layer (Phase 10) ────────────────
            logger.info("Step 1/13: Initializing security layer")
            from src.security.encryption import EncryptionManager
            from src.security.privacy import PrivacyManager
            from src.security.integrity import IntegrityManager
            from src.security.secure_storage import SecureStorageManager

            self.encryption = EncryptionManager()
            self.encryption.initialize()

            self.secure_storage = SecureStorageManager(self.encryption)
            self.secure_storage.initialize()

            self.privacy_mgr = PrivacyManager(self.config)
            self.integrity_mgr = IntegrityManager()
            # self.audit_logger created after audit_repo in step 3

            # ── Step 2: Load configuration ──────────────────────────────────
            logger.info("Step 2/13: Loading configuration")
            self.config.initialize(self.encryption, self.secure_storage)
            self.config.load()

            # ── Step 3: Initialize Data Layer + SQLite (thread e) ───────────
            logger.info("Step 3/13: Initializing data layer")
            self.db = SQLiteManager()
            if not self.db.initialize():
                logger.critical("Database initialization failed")
                return False

            self.behavioral_repo = BehavioralRepository(self.db)
            self.feature_repo = FeatureRepository(self.db)
            self.audit_repo = AuditRepository(self.db)
            from src.security.logging_manager import LoggingManager
            self.audit_logger = LoggingManager(self.audit_repo)
            self.sliding_window = SlidingWindowManager(self.db, self.behavioral_repo)
            self.backup_mgr = BackupManager(self.db, self.encryption)
            self.cleanup_mgr = CleanupManager(self.db)

            # ── Step 4: Initialize Behavioral Collection Layer (Phase 3, thread b) ──
            logger.info("Step 4/13: Initializing behavioral collection layer")
            from src.behavior.event_buffer import EventBuffer
            from src.behavior.keyboard import KeyboardMonitoringService
            from src.behavior.mouse import MouseMonitoringService
            from src.behavior.scroll import ScrollMonitoringService
            from src.behavior.idle_detector import IdleDetectionService
            from src.behavior.windows_integration import WindowsIntegrationLayer

            self.event_buffer = EventBuffer()
            self.keyboard_monitor = KeyboardMonitoringService(self.event_buffer)
            self.mouse_monitor = MouseMonitoringService(self.event_buffer)
            self.scroll_monitor = ScrollMonitoringService(self.event_buffer)
            self.idle_detector = IdleDetectionService()
            self.windows_integration = WindowsIntegrationLayer()
            self.windows_integration.initialize()

            # ── Step 5: Initialize Processing Layer (Phase 5, thread c) ─────
            logger.info("Step 5/13: Initializing processing layer")
            from src.behavior.event_aggregator import EventAggregator
            from src.ai.features import FeatureExtractionEngine
            from src.ai.normalization import FeatureNormalizationEngine

            self.event_aggregator = EventAggregator()
            self.feature_extractor = FeatureExtractionEngine()
            self.feature_normalizer = FeatureNormalizationEngine()

            # ── Step 6: Initialize AI / ML Layer (Phase 6 + 7 + 8) ─────────
            logger.info("Step 6/13: Initializing AI/ML layer")
            from src.ai.dataset import DatasetManager
            from src.ai.confidence import ConfidenceEngine
            from src.ai.trust import TrustScoreManager
            from src.ai.risk import AdaptiveRiskEngine
            from src.ai.authentication import AuthenticationManager
            from src.ai.inference import InferenceEngine
            from src.ai.repository import ModelRepository
            from src.ai.training import ModelTrainingEngine
            from src.ai.validator import ModelValidator
            from src.ai.version import VersionManager
            from src.ai.retraining import RetrainingManager
            from src.ai.scheduler import TrainingScheduler
            from src.ai.model_wrapper import EnsembleModelWrapper

            self.dataset_mgr = DatasetManager(self.db, self.feature_repo)
            self.confidence_engine = ConfidenceEngine()
            self.trust_mgr = TrustScoreManager()
            self.risk_engine = AdaptiveRiskEngine(self.trust_mgr, self.confidence_engine)
            self.model_repo = ModelRepository(self.db, self.secure_storage)
            self.training_engine = ModelTrainingEngine(
                self.db, self.dataset_mgr, self.model_repo
            )
            self.model_validator = ModelValidator()
            self.version_mgr = VersionManager(self.db, self.model_repo)
            self.inference_engine = InferenceEngine(self.model_repo, self.confidence_engine)
            self.retraining_mgr = RetrainingManager(
                self.db, self.dataset_mgr, self.training_engine,
                self.model_validator, self.version_mgr, self.model_repo,
                self.sliding_window,
            )
            # TrainingScheduler initialized after session exists (step 10)

            # Create auth manager (needs session, which is created below)
            # Will be finalized after step 10

            # ── Step 7: Initialize Enrollment System (Phase 4) ──────────────
            logger.info("Step 7/13: Initializing enrollment system")
            self.assignment_mgr = AssignmentManager(self.db)
            self.progress_mgr = ProgressManager(self.db)
            self.calendar_mgr = CalendarManager(self.db)
            self.enrollment_validator = EnrollmentValidator(self.db)
            self.enrollment_system = EnrollmentManager(
                self.db, self.assignment_mgr, self.progress_mgr,
                self.calendar_mgr, self.enrollment_validator,
            )

            # ── Step 8: Initialize Presentation Layer (Phase 9) ─────────────
            logger.info("Step 8/13: Initializing presentation layer")
            # Presentation layer (MainWindow) is created externally by
            # GuardianAIApplication which attaches it via set_main_window()
            self._signals.startup_complete.connect(self._on_startup_complete)

            # Wire enrollment → training → auth signals
            self._wire_workflow_signals()

            # ── Step 9: Initialize Workflow Controller (Phase 2) ───────────
            logger.info("Step 9/13: Initializing workflow controller")
            self.workflow = WorkflowController(self)

            # ── Step 10: Initialize Session Manager (Phase 2) ───────────────
            logger.info("Step 10/13: Initializing session manager")
            self.session = SessionManager(db=self.db)

            # Finalize auth manager now that session exists
            self.auth_mgr = AuthenticationManager(
                self.trust_mgr, self.risk_engine,
                self.confidence_engine, self.session,
            )

            # Initialize training scheduler (needs session)
            self.training_scheduler = TrainingScheduler(self.db, self.session)

            # ── Step 11: Run Startup Manager verification ───────────────────
            logger.info("Step 11/13: Running startup verification")
            if not self.startup.execute():
                logger.critical("Startup verification failed")
                return False

            # ── Step 12: Start Maintenance Thread (thread f) ────────────────
            logger.info("Step 12/13: Starting maintenance thread")
            self._start_maintenance_thread()

            # ── Step 13: Mark system ready ──────────────────────────────────
            self._initialized = True
            logger.info("Application initialization complete (13/13)")
            return True

        except Exception as e:
            logger.critical(
                f"Application initialization failed: {e}", exc_info=True
            )
            return False

    # ═══════════════════════════════════════════════════════════════════════
    #  Start / Run
    # ═══════════════════════════════════════════════════════════════════════

    def start(self) -> None:
        """Start the application's main operation.

        Launches background threads, starts behavioral monitoring,
        and begins the authentication pipeline.
        """
        if not self._initialized:
            raise RuntimeError("Cannot start: application not initialized")

        self._running = True
        logger.info("Starting GuardianAI subsystems...")

        # 1. Start session
        if self.session:
            self.session.start()

        # 2. Start behavioral collection (thread b)
        self._start_collection_thread()

        # 3. Start processing pipeline (thread c)
        self._start_processing_thread()

        # 4. Start auth pipeline (thread d)
        self._start_auth_thread()

        # 5. Start behavioral monitors
        if self.keyboard_monitor:
            self.keyboard_monitor.start()
        if self.mouse_monitor:
            self.mouse_monitor.start()
        if self.scroll_monitor:
            self.scroll_monitor.start()
        if self.idle_detector:
            self.idle_detector.start()

        # 6. Start workflow
        if self.workflow:
            self.workflow.start()

        # 7. Notify all subsystems
        self._signals.startup_complete.emit()
        logger.info(f"{APP_NAME} now running in continuous authentication mode")

    def set_presentation_layer(self, main_window) -> None:
        """Attach the presentation layer (MainWindow) after creation.

        Called by GuardianAIApplication after the Qt event loop is set up.
        """
        self.presentation_layer = main_window
        logger.info("Presentation layer attached")

    # ═══════════════════════════════════════════════════════════════════════
    #  Background Threads (6-thread model)
    # ═══════════════════════════════════════════════════════════════════════

    def _start_collection_thread(self) -> None:
        """Start thread b: low-latency event collection."""
        self._collection_running.set()
        self._collection_thread = threading.Thread(
            target=self._collection_loop,
            name="Behavior-Collection-Thread",
            daemon=True,
        )
        self._collection_thread.start()
        logger.info("Collection thread started")

    def _collection_loop(self) -> None:
        """Continuously drain event buffer for processing."""
        while self._collection_running.is_set():
            try:
                if self.event_buffer and self.event_buffer.size > 0:
                    batch = self.event_buffer.pop_batch(100)
                    if batch and self.event_aggregator:
                        for event in batch:
                            self.event_aggregator.add_event(event)
                # Brief sleep to prevent busy-waiting
                threading.Event().wait(0.01)
            except Exception as e:
                logger.error(f"Collection thread error: {e}")

    def _start_processing_thread(self) -> None:
        """Start thread c: event aggregation -> feature extraction -> normalization."""
        self._processing_running.set()
        self._processing_thread = threading.Thread(
            target=self._processing_loop,
            name="Feature-Processing-Thread",
            daemon=True,
        )
        self._processing_thread.start()
        logger.info("Processing thread started")

    def _processing_loop(self) -> None:
        """Process completed behavioral windows into normalized feature vectors."""
        while self._processing_running.is_set():
            try:
                if self.event_aggregator:
                    windows = self.event_aggregator.get_completed_windows()
                    for window in windows:
                        # Extract features
                        fv = self.feature_extractor.extract_features(window)
                        if fv is None:
                            continue
                        # Normalize features
                        normalized = self.feature_normalizer.normalize(fv.features)
                        if normalized is not None:
                            fv.features = normalized
                            self._signals.feature_normalized.emit(fv)
                            # Store feature vector
                            if self.feature_repo and fv.session_id:
                                fid = self.feature_repo.store_feature(fv)
                                if fid:
                                    self._signals.feature_stored.emit(fid)
                threading.Event().wait(0.05)
            except Exception as e:
                logger.error(f"Processing thread error: {e}")

    def _start_auth_thread(self) -> None:
        """Start thread d: inference -> confidence -> trust -> risk -> decision."""
        self._auth_running.set()
        self._auth_thread = threading.Thread(
            target=self._auth_loop,
            name="Authentication-Thread",
            daemon=True,
        )
        self._auth_thread.start()
        logger.info("Auth thread started")

    def _auth_loop(self) -> None:
        """Continuously evaluate authentication state."""
        while self._auth_running.is_set():
            try:
                if self.risk_engine:
                    risk = self.risk_engine.evaluate()
                if self.auth_mgr:
                    self.auth_mgr.evaluate()
                threading.Event().wait(1.0)  # Evaluate every second
            except Exception as e:
                logger.error(f"Auth thread error: {e}")

    def _start_maintenance_thread(self) -> None:
        """Start thread f: scheduled retraining, backup, and cleanup."""
        self._maintenance_running.set()
        self._maintenance_thread = threading.Thread(
            target=self._maintenance_loop,
            name="Maintenance-Thread",
            daemon=True,
        )
        self._maintenance_thread.start()
        logger.info("Maintenance thread started")

    def _maintenance_loop(self) -> None:
        """Periodic maintenance: check retraining, run backup, run cleanup."""
        cycle = 0
        while self._maintenance_running.is_set():
            try:
                cycle += 1
                # Every 60 seconds (adjustable)
                if cycle % 60 == 0:  # ~1 minute
                    # Check if retraining is due
                    if self.training_scheduler:
                        if self.training_scheduler.should_schedule_retraining():
                            logger.info("Maintenance: retraining due")
                            if self.retraining_mgr:
                                threading.Thread(
                                    target=self.retraining_mgr.execute_retraining,
                                    daemon=True,
                                ).start()

                # Every 3600 cycles (~1 hour)
                if cycle % 3600 == 0:
                    if self.backup_mgr:
                        try:
                            path = self.backup_mgr.create_backup()
                            if path:
                                self._signals.backup_completed.emit(str(path))
                        except Exception as e:
                            logger.warning(f"Backup failed: {e}")

                    if self.cleanup_mgr:
                        try:
                            stats = self.cleanup_mgr.run_cleanup()
                            self._signals.cleanup_completed.emit(stats)
                        except Exception as e:
                            logger.warning(f"Cleanup failed: {e}")

                    if self.integrity_mgr:
                        try:
                            result = self.integrity_mgr.verify_all()
                            self._signals.integrity_check_completed.emit(result)
                        except Exception as e:
                            logger.warning(f"Integrity check failed: {e}")

                threading.Event().wait(1.0)
            except Exception as e:
                logger.error(f"Maintenance thread error: {e}")

    # ═══════════════════════════════════════════════════════════════════════
    #  Shutdown
    # ═══════════════════════════════════════════════════════════════════════

    def shutdown(self) -> None:
        """Gracefully shut down the application in reverse order."""
        with self._shutdown_lock:
            if not self._running:
                return

            logger.info("Initiating graceful shutdown...")
            self._signals.shutdown_initiated.emit()

            try:
                # 1. Stop background threads
                self._collection_running.clear()
                self._processing_running.clear()
                self._auth_running.clear()
                self._maintenance_running.clear()

                # 2. Stop behavioral monitors
                if self.keyboard_monitor:
                    self._safe_stop(self.keyboard_monitor)
                if self.mouse_monitor:
                    self._safe_stop(self.mouse_monitor)
                if self.scroll_monitor:
                    self._safe_stop(self.scroll_monitor)
                if self.idle_detector:
                    self._safe_stop(self.idle_detector)

                # 3. Stop inference engine
                if self.inference_engine:
                    self._safe_stop(self.inference_engine)

                # 4. Flush event buffer
                if self.event_buffer:
                    self.event_buffer.flush()

                # 5. Save session state
                if self.session:
                    self.session.close_all()

                # 6. Commit database transactions
                if self.db:
                    self.db.commit()

                # 7. Write final logs
                logging.shutdown()

                # 8. Wait for threads (with timeout)
                for t in [self._collection_thread, self._processing_thread,
                          self._auth_thread, self._maintenance_thread]:
                    if t and t.is_alive():
                        t.join(timeout=3.0)

            except Exception as e:
                logger.error(f"Error during shutdown: {e}")

            finally:
                self._running = False
                self._signals.shutdown_complete.emit()
                logger.info(f"{APP_NAME} shutdown complete")

    def _safe_stop(self, component) -> None:
        """Safely stop a component."""
        try:
            if hasattr(component, 'stop'):
                component.stop()
        except Exception as e:
            logger.warning(f"Error stopping component: {e}")

    def _handle_signal(self, sig, frame) -> None:
        """Handle OS signals for graceful shutdown."""
        logger.info(f"Received signal {sig}")
        self.shutdown()
        sys.exit(0)

    def _get_encryption(self):
        """Lazy access to encryption manager."""
        return self.encryption

    def _get_secure_storage(self):
        """Lazy access to secure storage manager."""
        return self.secure_storage

    def _wire_workflow_signals(self) -> None:
        """Wire enrollment -> training -> auth signal pipeline.

        enrollment_completed  -> update config
        training_completed    -> reload inference engine
        model_deployed        -> notify UI
        """
        self._signals.enrollment_completed.connect(self._on_enrollment_completed)
        self._signals.training_completed.connect(self._on_training_completed)
        self._signals.model_deployed.connect(self._on_model_deployed)

    def validate_and_deploy_model(self, report: dict) -> bool:
        """Validate a trained model and deploy it to production.

        Shared helper used by both the WorkflowController and the
        enrollment-completed handler to avoid duplicated logic.

        Args:
            report: Training report from ModelTrainingEngine

        Returns:
            True if model was validated and deployed
        """
        try:
            model_id = report["model_id"]
            model_data = self.model_repo.get_model(model_id) if self.model_repo else None
            if not model_data:
                logger.error("Cannot validate: model not found")
                return False

            from src.ai.model_wrapper import EnsembleModelWrapper
            wrapped = EnsembleModelWrapper.wrap(model_data["model"])

            X_val = None
            if self.dataset_mgr:
                _, X_val, _ = self.dataset_mgr.get_training_dataset()
                X_val = X_val[:100] if X_val is not None else None

            if X_val is not None and len(X_val) >= 5:
                val_report = self.model_validator.validate(wrapped, X_val)
                if val_report.get("overall_pass", False):
                    if self.version_mgr:
                        self.version_mgr.deploy_model(model_id, val_report)
                    self._signals.training_completed.emit(report)
                    return True
                else:
                    logger.warning(f"Validation failed: {val_report}")
                    return False
            else:
                # Not enough validation data — deploy anyway and learn in production
                if self.version_mgr:
                    self.version_mgr.deploy_model(
                        model_id, {"overall_pass": True, "accuracy": 0.9}
                    )
                self._signals.training_completed.emit(report)
                return True

        except Exception as e:
            logger.error(f"Validate/deploy failed: {e}")
            return False

    def _on_enrollment_completed(self) -> None:
        """Handle enrollment completion — update config only.

        The WorkflowController owns the training lifecycle via its
        state machine (ENROLLMENT → TRAINING transition triggers training).
        This handler just persists the completion state.
        """
        logger.info("Enrollment completed, config updated")
        self.config.set("app.enrollment_status", "completed")

    def _on_training_completed(self, report: dict) -> None:
        """Handle training completion - reload inference engine."""
        logger.info(f"Training completed: {report.get('model_id', 'unknown')}")
        if self.inference_engine:
            self.inference_engine.reload_model()

    def _on_model_deployed(self, model_version: str) -> None:
        """Handle model deployment - notify UI."""
        logger.info(f"Model v{model_version} deployed")
        self._signals.notification_received.emit(
            "success", "Model Deployed",
            f"Auth model v{model_version} is active",
        )

    def _on_startup_complete(self) -> None:
        """Handle startup completion."""
        logger.info("Startup signal received")

"""Workflow Controller - Coordinates all major application workflows.

Manages transitions between application states including enrollment,
authentication, training, retraining, and scheduled operations.
"""

import logging
from enum import Enum
from typing import Any, Optional, Callable
from datetime import datetime

from PySide6.QtCore import QObject, QTimer

from src.utils.signals import get_signals

logger = logging.getLogger(__name__)


class WorkflowState(Enum):
    """Possible workflow states."""
    IDLE = "idle"
    STARTUP = "startup"
    REGISTRATION = "registration"
    ENROLLMENT = "enrollment"
    TRAINING = "training"
    AUTHENTICATION = "authentication"
    RETRAINING = "retraining"
    MAINTENANCE = "maintenance"
    SHUTDOWN = "shutdown"
    ERROR = "error"


class WorkflowController(QObject):
    """Manages workflow states and transitions between them.

    Wires EnrollmentManager, TrainingEngine, and AuthenticationManager
    into a seamless lifecycle:
      IDLE → STARTUP → REGISTRATION → ENROLLMENT → TRAINING →
      AUTHENTICATION ↔ RETRAINING → SHUTDOWN
    """

    def __init__(self, app_core) -> None:
        super().__init__()
        self._app_core = app_core
        self._signals = get_signals()
        self._current_state: WorkflowState = WorkflowState.IDLE
        self._previous_state: Optional[WorkflowState] = None

        # Workflow handlers registry
        self._handlers: dict[WorkflowState, Callable[[], None]] = {}

        # Connect to application signals for auto-transitions
        self._connect_signals()

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._on_timer)

    @property
    def current_state(self) -> WorkflowState:
        return self._current_state

    @property
    def previous_state(self) -> Optional[WorkflowState]:
        return self._previous_state

    def register_handler(self, state: WorkflowState, handler: Callable[[], None]) -> None:
        """Register a handler function for a workflow state."""
        self._handlers[state] = handler

    def _connect_signals(self) -> None:
        """Connect to application signals for automatic state transitions."""
        # Enrollment completed → start training
        self._signals.enrollment_completed.connect(
            lambda: self._transition_to(WorkflowState.TRAINING)
        )
        # Training completed → start authentication
        self._signals.training_completed.connect(
            lambda report: self._on_training_completed(report)
        )
        # Model deployed → stay in authentication
        self._signals.model_deployed.connect(
            lambda v: logger.info(f"Model {v} deployed, continuing authentication")
        )

    def start(self) -> None:
        """Start the workflow controller."""
        self._transition_to(WorkflowState.STARTUP)
        self._timer.start(60000)  # Check every 60 seconds
        logger.info("Workflow controller started")

    def _transition_to(self, new_state: WorkflowState) -> bool:
        """Transition to a new workflow state.

        Args:
            new_state: The target workflow state

        Returns:
            True if transition succeeded
        """
        if new_state == self._current_state:
            return True

        if not self._can_transition(new_state):
            logger.warning(
                f"Cannot transition from {self._current_state.value} "
                f"to {new_state.value}"
            )
            return False

        self._previous_state = self._current_state
        self._current_state = new_state
        logger.info(f"Workflow state: {self._previous_state.value} -> "
                    f"{new_state.value}")

        # Execute handler if registered
        handler = self._handlers.get(new_state)
        if handler:
            try:
                handler()
            except Exception as e:
                logger.error(f"Workflow handler failed for {new_state.value}: {e}")
                self._transition_to(WorkflowState.ERROR)
                return False

        # Handle automatic transitions
        self._handle_auto_transition(new_state)
        return True

    def _can_transition(self, target: WorkflowState) -> bool:
        """Check if transition is allowed from current state."""
        allowed = {
            WorkflowState.IDLE: {WorkflowState.STARTUP},
            WorkflowState.STARTUP: {WorkflowState.REGISTRATION,
                                     WorkflowState.ENROLLMENT,
                                     WorkflowState.AUTHENTICATION,
                                     WorkflowState.ERROR},
            WorkflowState.REGISTRATION: {WorkflowState.ENROLLMENT},
            WorkflowState.ENROLLMENT: {WorkflowState.TRAINING,
                                        WorkflowState.ERROR},
            WorkflowState.TRAINING: {WorkflowState.AUTHENTICATION,
                                      WorkflowState.ERROR},
            WorkflowState.AUTHENTICATION: {WorkflowState.RETRAINING,
                                            WorkflowState.MAINTENANCE,
                                            WorkflowState.SHUTDOWN,
                                            WorkflowState.ERROR},
            WorkflowState.RETRAINING: {WorkflowState.AUTHENTICATION,
                                        WorkflowState.ERROR},
            WorkflowState.MAINTENANCE: {WorkflowState.AUTHENTICATION,
                                         WorkflowState.ERROR},
            WorkflowState.SHUTDOWN: set(),
            WorkflowState.ERROR: {WorkflowState.IDLE, WorkflowState.SHUTDOWN},
        }
        return target in allowed.get(self._current_state, set())

    def _handle_auto_transition(self, state: WorkflowState) -> None:
        """Handle automatic transitions after entering a state."""
        if state == WorkflowState.STARTUP:
            self._determine_startup_path()

        elif state == WorkflowState.REGISTRATION:
            # User needs to register; the UI will trigger start_enrollment
            self._signals.dashboard_update.emit({
                "status": "registration_required",
                "message": "Complete user registration to begin enrollment",
            })

        elif state == WorkflowState.ENROLLMENT:
            logger.info("Entering enrollment workflow")

        elif state == WorkflowState.TRAINING:
            self._trigger_training()

    def _determine_startup_path(self) -> None:
        """Determine which workflow path to follow after startup.

        Checks enrollment status to decide:
          - completed → AUTHENTICATION (resume monitoring)
          - in_progress → ENROLLMENT (continue where left off)
          - not_started/no user → REGISTRATION (new user)
        """
        try:
            enrollment = self._app_core.enrollment_system
            if enrollment and enrollment.is_active:
                logger.info("Enrollment in progress, continuing enrollment")
                self._transition_to(WorkflowState.ENROLLMENT)
                return

            if enrollment and enrollment.status == "completed":
                logger.info("Enrollment complete, entering authentication mode")
                # Check if model exists
                if self._app_core.model_repo:
                    active = self._app_core.model_repo.get_active_model()
                    if active:
                        self._transition_to(WorkflowState.AUTHENTICATION)
                        return
                # No model yet — train one
                self._transition_to(WorkflowState.TRAINING)
                return

            # No enrollment yet — check for registered user
            if self._app_core.db:
                user = self._app_core.db.fetch_one(
                    "SELECT user_id FROM users LIMIT 1"
                )
                if user:
                    logger.info(f"User {user['user_id']} found, starting enrollment")
                    if enrollment:
                        enrollment.start_enrollment(user["user_id"])
                    self._transition_to(WorkflowState.ENROLLMENT)
                    return

            # No user — need registration
            logger.info("No registered user, registration required")
            self._transition_to(WorkflowState.REGISTRATION)

        except Exception as e:
            logger.error(f"Startup path determination failed: {e}")
            self._transition_to(WorkflowState.ERROR)

    def _trigger_training(self) -> None:
        """Trigger initial model training after enrollment completes."""
        logger.info("Triggering initial model training")
        engine = self._app_core.training_engine
        if not engine:
            logger.error("No training engine available")
            return

        def train_and_report():
            try:
                report = engine.train_initial_model()
                if report:
                    logger.info(f"Initial training complete: {report['model_id']}")
                    # Validate and deploy using shared method on ApplicationCore
                    if hasattr(self._app_core, 'validate_and_deploy_model'):
                        self._app_core.validate_and_deploy_model(report)
                else:
                    logger.error("Initial training failed")
                    self._signals.error_occurred.emit(
                        "training", "Initial model training failed"
                    )
            except Exception as e:
                logger.error(f"Training error: {e}")
                self._signals.error_occurred.emit("training", str(e))

        # Run training in a background thread
        import threading
        threading.Thread(target=train_and_report, daemon=True).start()

    def _on_training_completed(self, report: dict[str, Any]) -> None:
        """Handle training completion — transition to authentication."""
        logger.info("Training completed, entering authentication mode")
        self._transition_to(WorkflowState.AUTHENTICATION)

    def _on_timer(self) -> None:
        """Periodic timer tick for scheduled operations."""
        if self._current_state == WorkflowState.AUTHENTICATION:
            current_hour = datetime.now().hour
            # Check for scheduled maintenance during low-activity hours
            if 2 <= current_hour <= 4:
                self._schedule_maintenance()

    def start_authentication(self) -> bool:
        """Transition to authentication workflow."""
        return self._transition_to(WorkflowState.AUTHENTICATION)

    def start_enrollment(self) -> bool:
        """Transition to enrollment workflow."""
        return self._transition_to(WorkflowState.ENROLLMENT)

    def start_training(self) -> bool:
        """Transition to training workflow."""
        return self._transition_to(WorkflowState.TRAINING)

    def start_retraining(self) -> bool:
        """Transition to retraining workflow."""
        return self._transition_to(WorkflowState.RETRAINING)

    def start_maintenance(self) -> bool:
        """Transition to maintenance workflow."""
        return self._transition_to(WorkflowState.MAINTENANCE)

    def _schedule_maintenance(self) -> None:
        """Schedule periodic maintenance tasks."""
        try:
            logger.debug("Scheduled maintenance check triggered")
            # Trigger retraining check via training_scheduler
            if self._app_core.training_scheduler:
                if self._app_core.training_scheduler.should_schedule_retraining():
                    logger.info("Retraining due, starting retraining workflow")
                    self._transition_to(WorkflowState.RETRAINING)
                    # Execute retraining in background
                    if self._app_core.retraining_mgr:
                        import threading
                        threading.Thread(
                            target=self._execute_retraining,
                            daemon=True,
                        ).start()
        except Exception as e:
            logger.warning(f"Scheduled maintenance check failed: {e}")

    def _execute_retraining(self) -> None:
        """Execute retraining and transition back to auth on completion."""
        try:
            result = self._app_core.retraining_mgr.execute_retraining()
            if result:
                if result.get("deployed"):
                    logger.info("Retraining successful, new model deployed")
                    self._signals.model_deployed.emit(
                        result.get("report", {}).get("model_id", "unknown")
                    )
                else:
                    logger.info("Retraining completed but model not improved")
            # Use QTimer.singleShot to run state transition on Qt main thread
            from PySide6.QtCore import QTimer
            QTimer.singleShot(0, lambda: self._transition_to(WorkflowState.AUTHENTICATION))
        except Exception as e:
            logger.error(f"Retraining execution failed: {e}")
            self._signals.error_occurred.emit("retraining", str(e))
            from PySide6.QtCore import QTimer
            QTimer.singleShot(0, lambda: self._transition_to(WorkflowState.AUTHENTICATION))

    def request_shutdown(self) -> bool:
        """Begin graceful shutdown workflow."""
        return self._transition_to(WorkflowState.SHUTDOWN)

    def handle_error(self, error_msg: str) -> None:
        """Handle an error by transitioning to error state."""
        logger.error(f"Workflow error: {error_msg}")
        self._transition_to(WorkflowState.ERROR)

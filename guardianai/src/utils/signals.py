"""Application-wide signal/event definitions using PySide6 Signal system.

All inter-component communication uses these signals to maintain loose coupling.
"""

from PySide6.QtCore import QObject, Signal
from typing import Any, Optional
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class BehavioralEvent:
    """Raw behavioral event from monitoring services."""
    event_type: str
    timestamp: datetime
    data: dict[str, Any] = field(default_factory=dict)
    session_id: Optional[str] = None


@dataclass
class FeatureVector:
    """Extracted and normalized feature vector."""
    features: list[float]
    timestamp: datetime
    session_id: Optional[str] = None
    source: str = "unknown"
    trust_level: str = "medium"


@dataclass
class AuthDecision:
    """Authentication decision payload."""
    status: str
    confidence: float
    trust_score: float
    risk_level: str
    timestamp: datetime
    session_id: Optional[str] = None
    details: dict[str, Any] = field(default_factory=dict)


class ApplicationSignals(QObject):
    """Central signal bus for inter-component communication."""

    # ── Behavioral Events ──────────────────────────────────────────────────

    keyboard_event = Signal(BehavioralEvent)
    mouse_event = Signal(BehavioralEvent)
    scroll_event = Signal(BehavioralEvent)
    idle_event = Signal(BehavioralEvent)

    # ── Feature Pipeline ────────────────────────────────────────────────────

    feature_extracted = Signal(FeatureVector)
    feature_normalized = Signal(FeatureVector)
    feature_stored = Signal(str)  # feature_id

    # ── Authentication ──────────────────────────────────────────────────────

    inference_completed = Signal(dict)  # prediction result
    confidence_updated = Signal(float)
    trust_updated = Signal(float)
    risk_updated = Signal(str)
    auth_decision = Signal(AuthDecision)
    auth_status_changed = Signal(str)  # new status

    # ── Session ─────────────────────────────────────────────────────────────

    session_started = Signal(str)  # session_id
    session_ended = Signal(str)   # session_id
    session_locked = Signal()
    session_unlocked = Signal()

    # ── Enrollment ──────────────────────────────────────────────────────────

    enrollment_started = Signal()
    enrollment_progress = Signal(float)  # 0.0 - 1.0
    enrollment_completed = Signal()
    assignment_due = Signal(str)  # assignment description
    assignment_completed = Signal(str)  # assignment_id

    # ── Model Training ──────────────────────────────────────────────────────

    training_started = Signal()
    training_progress = Signal(float)
    training_completed = Signal(dict)  # training report
    validation_completed = Signal(dict)  # validation report
    model_deployed = Signal(str)   # model version
    model_rollback = Signal(str)   # rolled back version

    # ── System ──────────────────────────────────────────────────────────────

    startup_complete = Signal()
    shutdown_initiated = Signal()
    shutdown_complete = Signal()
    error_occurred = Signal(str, str)  # component, error_msg
    warning_occurred = Signal(str, str)  # component, warning_msg

    # ── Maintenance ─────────────────────────────────────────────────────────

    backup_completed = Signal(str)  # backup path
    cleanup_completed = Signal(dict)  # cleanup stats
    integrity_check_completed = Signal(dict)  # check results

    # ── UI Updates ──────────────────────────────────────────────────────────

    notification_received = Signal(str, str, str)  # type, title, message
    dashboard_update = Signal(dict)
    analytics_update = Signal(dict)


# Global singleton instance
_signals_instance: Optional[ApplicationSignals] = None


def get_signals() -> ApplicationSignals:
    """Get the global ApplicationSignals singleton."""
    global _signals_instance
    if _signals_instance is None:
        _signals_instance = ApplicationSignals()
    return _signals_instance

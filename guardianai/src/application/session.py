"""Session Manager - Tracks active desktop sessions and manages session lifecycle.

Creates, closes, and tracks authentication sessions, detects session changes
from the operating system, and associates behavioral events with sessions.
"""

import logging
import uuid
from datetime import datetime
from typing import Optional
from dataclasses import dataclass, field

from PySide6.QtCore import QObject, QTimer

from src.utils.signals import get_signals
from src.utils.constants import IDLE_THRESHOLD_SECONDS

logger = logging.getLogger(__name__)


@dataclass
class Session:
    """Represents a single desktop authentication session."""
    session_id: str
    user_id: str
    start_time: datetime
    end_time: Optional[datetime] = None
    duration_seconds: float = 0.0
    auth_status: str = "monitoring"
    average_trust_score: float = 0.0
    is_active: bool = True
    event_count: int = 0
    last_activity_time: Optional[datetime] = None
    idle_seconds: float = 0.0
    metadata: dict = field(default_factory=dict)


class SessionManager(QObject):
    """Manages authentication sessions throughout the application lifecycle.

    Persists session records to the SQLite 'sessions' table for reliable
    session-based enrollment counting and historical tracking.
    """

    def __init__(self, db=None) -> None:
        """Initialize the session manager.

        Args:
            db: Optional SQLiteManager for persisting sessions to the DB.
                 If None, sessions are only kept in-memory (no persistence).
        """
        super().__init__()
        self._db = db
        self._signals = get_signals()
        self._sessions: dict[str, Session] = {}
        self._current_session_id: Optional[str] = None
        self._user_id: Optional[str] = None

        # Idle detection timer
        self._idle_timer = QTimer(self)
        self._idle_timer.setInterval(5000)  # check every 5 seconds
        self._idle_timer.timeout.connect(self._check_idle)

    @property
    def current_session(self) -> Optional[Session]:
        if self._current_session_id and self._current_session_id in self._sessions:
            return self._sessions[self._current_session_id]
        return None

    @property
    def current_session_id(self) -> Optional[str]:
        return self._current_session_id

    @property
    def user_id(self) -> Optional[str]:
        return self._user_id

    def set_user(self, user_id: str) -> None:
        """Set the current authenticated user."""
        self._user_id = user_id

    def start(self) -> None:
        """Start session monitoring."""
        self._idle_timer.start()
        logger.info("Session manager started")

    def create_session(self) -> str:
        """Create a new authentication session.

        Returns:
            The new session ID.
        """
        if not self._user_id:
            self._user_id = "default_user"

        session_id = str(uuid.uuid4())
        now = datetime.now()
        now_iso = now.isoformat()
        session = Session(
            session_id=session_id,
            user_id=self._user_id,
            start_time=now,
            last_activity_time=now,
        )
        self._sessions[session_id] = session
        self._current_session_id = session_id

        # Persist to DB
        if self._db:
            try:
                self._db.execute(
                    """INSERT INTO sessions 
                    (session_id, user_id, start_time, authentication_status)
                    VALUES (?, ?, ?, 'monitoring')""",
                    (session_id, self._user_id, now_iso),
                )
            except Exception as e:
                logger.warning(f"Failed to persist session to DB: {e}")

        self._signals.session_started.emit(session_id)
        logger.debug(f"Session created: {session_id}")
        return session_id

    def close_session(self, session_id: Optional[str] = None) -> None:
        """Close a session and record its duration."""
        sid = session_id or self._current_session_id
        if not sid or sid not in self._sessions:
            return

        session = self._sessions[sid]
        session.end_time = datetime.now()
        session.duration_seconds = (session.end_time - session.start_time).total_seconds()
        session.is_active = False

        # Persist end_time and duration to DB
        if self._db:
            try:
                self._db.execute(
                    """UPDATE sessions SET 
                    end_time = ?, duration_seconds = ?, authentication_status = ?
                    WHERE session_id = ?""",
                    (session.end_time.isoformat(), session.duration_seconds,
                     session.auth_status, sid),
                )
            except Exception as e:
                logger.warning(f"Failed to persist session close to DB: {e}")

        self._signals.session_ended.emit(sid)
        logger.debug(f"Session closed: {sid} ({session.duration_seconds:.1f}s)")

        if sid == self._current_session_id:
            self._current_session_id = None

    def close_all(self) -> None:
        """Close all active sessions."""
        for sid in list(self._sessions.keys()):
            if self._sessions[sid].is_active:
                self.close_session(sid)
        logger.info("All sessions closed")

    def record_activity(self, session_id: Optional[str] = None) -> None:
        """Record user activity timestamp for a session."""
        sid = session_id or self._current_session_id
        if sid and sid in self._sessions:
            self._sessions[sid].last_activity_time = datetime.now()
            self._sessions[sid].idle_seconds = 0.0
            self._sessions[sid].event_count += 1

    def update_trust_score(self, trust_score: float,
                           session_id: Optional[str] = None) -> None:
        """Update the trust score for a session."""
        sid = session_id or self._current_session_id
        if sid and sid in self._sessions:
            self._sessions[sid].average_trust_score = trust_score
            # Persist to DB
            if self._db:
                try:
                    self._db.execute(
                        "UPDATE sessions SET average_trust_score = ? WHERE session_id = ?",
                        (trust_score, sid),
                    )
                except Exception as e:
                    logger.warning(f"Failed to persist trust score to DB: {e}")

    def update_auth_status(self, status: str,
                           session_id: Optional[str] = None) -> None:
        """Update authentication status for a session."""
        sid = session_id or self._current_session_id
        if sid and sid in self._sessions:
            old_status = self._sessions[sid].auth_status
            self._sessions[sid].auth_status = status
            # Persist to DB
            if self._db:
                try:
                    self._db.execute(
                        "UPDATE sessions SET authentication_status = ? WHERE session_id = ?",
                        (status, sid),
                    )
                except Exception as e:
                    logger.warning(f"Failed to persist auth status to DB: {e}")
            if old_status != status:
                self._signals.auth_status_changed.emit(status)

    def _check_idle(self) -> None:
        """Check if the current session is idle."""
        session = self.current_session
        if not session or not session.last_activity_time:
            return

        elapsed = (datetime.now() - session.last_activity_time).total_seconds()
        session.idle_seconds = elapsed

        if elapsed > IDLE_THRESHOLD_SECONDS:
            self._signals.idle_event.emit(
                self._create_idle_event(session.session_id, elapsed)
            )

    def _create_idle_event(self, session_id: str, idle_duration: float):
        """Create an idle behavioral event."""
        from src.utils.signals import BehavioralEvent
        return BehavioralEvent(
            event_type="idle",
            timestamp=datetime.now(),
            data={"idle_duration": idle_duration},
            session_id=session_id,
        )

    def get_session(self, session_id: str) -> Optional[Session]:
        """Get a session by ID."""
        return self._sessions.get(session_id)

    def get_recent_sessions(self, limit: int = 10) -> list[Session]:
        """Get the most recent sessions."""
        sorted_sessions = sorted(
            [s for s in self._sessions.values() if s.end_time],
            key=lambda s: s.end_time or s.start_time,
            reverse=True
        )
        return sorted_sessions[:limit]

    def get_stats(self) -> dict:
        """Get session statistics."""
        total = len(self._sessions)
        active = sum(1 for s in self._sessions.values() if s.is_active)
        total_duration = sum(
            s.duration_seconds for s in self._sessions.values()
        )
        return {
            "total_sessions": total,
            "active_sessions": active,
            "total_duration_seconds": total_duration,
            "current_session_id": self._current_session_id,
        }

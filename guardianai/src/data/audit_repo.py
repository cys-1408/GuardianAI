"""Audit Repository - Stores authentication history and important security events.

Creates timestamped immutable audit entries for all security-relevant
application activities and authentication decisions.
"""

import json
import logging
from datetime import datetime
from typing import Any, Optional

from src.data.sqlite_manager import SQLiteManager

logger = logging.getLogger(__name__)


class AuditRepository:
    """Repository for audit logging and security event storage."""

    def __init__(self, db: SQLiteManager) -> None:
        self._db = db

    def record_event(self, event_type: str, severity: str, description: str,
                     metadata: Optional[dict] = None) -> int:
        """Record an audit event.

        Args:
            event_type: Type of event
            severity: Severity level
            description: Event description
            metadata: Optional structured data

        Returns:
            Log entry ID
        """
        log_id = self._db.insert(
            """INSERT INTO audit_logs (timestamp, component, severity, description, metadata)
            VALUES (datetime('now'), ?, ?, ?, ?)""",
            (event_type, severity, description,
             json.dumps(metadata or {})),
        )
        return log_id

    def record_auth_event(self, session_id: str, confidence: float,
                          trust_score: float, result: str,
                          risk_level: str) -> int:
        """Record an authentication event.

        Args:
            session_id: Session identifier
            confidence: Confidence score
            trust_score: Trust score
            result: Authentication result
            risk_level: Risk level

        Returns:
            Auth history entry ID
        """
        auth_id = self._db.insert(
            """INSERT INTO authentication_history 
            (session_id, timestamp, confidence_score, trust_score, auth_result, risk_level)
            VALUES (?, datetime('now'), ?, ?, ?, ?)""",
            (session_id, confidence, trust_score, result, risk_level),
        )
        return auth_id

    def get_events(self, limit: int = 100, offset: int = 0,
                   severity: Optional[str] = None) -> list[dict[str, Any]]:
        """Get audit events with optional filtering.

        Args:
            limit: Maximum results
            offset: Result offset
            severity: Optional severity filter

        Returns:
            List of audit event dicts
        """
        if severity:
            return self._db.fetch_all(
                """SELECT * FROM audit_logs WHERE severity = ? 
                ORDER BY timestamp DESC LIMIT ? OFFSET ?""",
                (severity, limit, offset),
            )
        return self._db.fetch_all(
            "SELECT * FROM audit_logs ORDER BY timestamp DESC LIMIT ? OFFSET ?",
            (limit, offset),
        )

    def get_auth_history(self, limit: int = 100) -> list[dict[str, Any]]:
        """Get recent authentication history.

        Args:
            limit: Maximum results

        Returns:
            List of auth history dicts
        """
        return self._db.fetch_all(
            "SELECT * FROM authentication_history ORDER BY timestamp DESC LIMIT ?",
            (limit,),
        )

    def get_auth_stats(self) -> dict[str, Any]:
        """Get authentication statistics."""
        total = self._db.fetch_one(
            "SELECT COUNT(*) as count FROM authentication_history"
        )
        trusted = self._db.fetch_one(
            """SELECT COUNT(*) as count FROM authentication_history 
            WHERE auth_result = 'authenticated'"""
        )
        high_risk = self._db.fetch_one(
            """SELECT COUNT(*) as count FROM authentication_history 
            WHERE risk_level IN ('high', 'critical')"""
        )
        return {
            "total_auths": total["count"] if total else 0,
            "trusted": trusted["count"] if trusted else 0,
            "high_risk_events": high_risk["count"] if high_risk else 0,
        }

    def get_event_count(self) -> int:
        """Get total count of audit events."""
        row = self._db.fetch_one("SELECT COUNT(*) as count FROM audit_logs")
        return row["count"] if row else 0

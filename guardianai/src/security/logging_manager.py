"""Logging Manager - Records operational and security-related events.

Organizes logs according to severity level, timestamp, and originating
component with support for audit-grade logging.
"""

import logging
import json
from datetime import datetime
from typing import Any
from pathlib import Path

from src.utils.constants import LOGS_DIR, LOG_MAX_BYTES, LOG_BACKUP_COUNT
from src.data.audit_repo import AuditRepository

logger = logging.getLogger(__name__)


class LoggingManager:
    """Centralized logging service with audit integration."""

    def __init__(self, audit_repo: AuditRepository) -> None:
        self._audit_repo = audit_repo
        self._log_buffer: list[dict[str, Any]] = []
        self._buffer_size = 100

    def initialize(self) -> None:
        """Initialize logging subsystem."""
        log_file = LOGS_DIR / "guardianai.log"
        handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=LOG_MAX_BYTES,
            backupCount=LOG_BACKUP_COUNT,
            encoding='utf-8',
        )
        formatter = logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
        )
        handler.setFormatter(formatter)

        root_logger = logging.getLogger()
        root_logger.addHandler(handler)
        root_logger.setLevel(logging.INFO)

        logger.info(f"Logging initialized: {log_file}")

    def log_event(self, component: str, severity: str, message: str,
                  details: dict | None = None) -> None:
        """Log an event with structured data.

        Args:
            component: Originating component name
            severity: Severity level (information, warning, error, critical)
            message: Log message
            details: Optional structured details
        """
        entry = {
            "timestamp": datetime.now().isoformat(),
            "component": component,
            "severity": severity.upper(),
            "message": message,
            "details": details or {},
        }

        # Write to standard logging
        log_level = getattr(logging, severity.upper(), logging.INFO)
        logger.log(log_level, f"[{component}] {message}")

        # Buffer for audit
        self._log_buffer.append(entry)
        if len(self._log_buffer) >= self._buffer_size:
            self._flush_buffer()

    def log_security_event(self, event_type: str, message: str,
                           details: dict | None = None) -> None:
        """Log a security-relevant event.

        Args:
            event_type: Type of security event
            message: Event description
            details: Optional structured details
        """
        entry = {
            "timestamp": datetime.now().isoformat(),
            "event_type": event_type,
            "message": message,
            "details": details or {},
        }
        logger.warning(f"[SECURITY] {event_type}: {message}")

        # Store in audit repository
        try:
            self._audit_repo.record_event(
                event_type=event_type,
                severity="warning",
                description=message,
                metadata=details or {},
            )
        except Exception as e:
            logger.error(f"Failed to store audit event: {e}")

    def flush(self) -> None:
        """Flush all buffered log entries."""
        self._flush_buffer()

    def _flush_buffer(self) -> None:
        """Write buffered log entries to audit storage."""
        if not self._log_buffer:
            return

        try:
            for entry in self._log_buffer:
                self._audit_repo.record_event(
                    event_type="system_log",
                    severity=entry["severity"],
                    description=entry["message"],
                    metadata={
                        "component": entry["component"],
                        "details": entry.get("details", {}),
                    },
                )
            self._log_buffer.clear()
        except Exception as e:
            logger.error(f"Failed to flush log buffer: {e}")

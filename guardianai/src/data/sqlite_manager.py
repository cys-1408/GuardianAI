"""SQLite Manager - Centralized database access for GuardianAI.

Manages database connections, executes queries, handles transactions,
optimizes performance, and maintains database consistency.
"""

import sqlite3
import logging
import threading
import time
from pathlib import Path
from typing import Any, Optional, Callable

from src.utils.constants import DB_PATH

logger = logging.getLogger(__name__)


class DatabaseError(Exception):
    """Raised when database operations fail."""
    pass


class SQLiteManager:
    """Centralized SQLite database manager with thread-safe access (singleton)."""

    _instance = None
    _instance_lock = threading.Lock()

    def __new__(cls) -> 'SQLiteManager':
        if cls._instance is None:
            with cls._instance_lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
                    cls._instance._db_path: Path = DB_PATH
                    cls._instance._local = threading.local()
                    cls._instance._lock = threading.RLock()
        return cls._instance

    def __init__(self) -> None:
        # Only initialize once via singleton pattern
        if not hasattr(self, '_init_done'):
            self._db_path = DB_PATH
            self._local = threading.local()
            self._lock = threading.RLock()
            self._initialized = False
            self._init_done = True

    @property
    def is_initialized(self) -> bool:
        return self._initialized

    def initialize(self) -> bool:
        """Initialize database and create schema.

        Returns:
            True if initialization succeeded
        """
        try:
            self._db_path.parent.mkdir(parents=True, exist_ok=True)
            self._create_tables()
            self._initialized = True
            logger.info(f"Database initialized: {self._db_path}")
            return True
        except sqlite3.Error as e:
            logger.error(f"Failed to initialize database: {e}")
            return False

    def _get_connection(self) -> sqlite3.Connection:
        """Get a thread-local database connection."""
        if not hasattr(self._local, 'connection') or self._local.connection is None:
            self._local.connection = sqlite3.connect(
                str(self._db_path),
                timeout=30,
                detect_types=sqlite3.PARSE_DECLTYPES,
            )
            self._local.connection.execute("PRAGMA journal_mode=WAL")
            self._local.connection.execute("PRAGMA foreign_keys=ON")
            self._local.connection.execute("PRAGMA synchronous=NORMAL")
            self._local.connection.execute("PRAGMA cache_size=-64000")  # 64MB
            self._local.connection.row_factory = sqlite3.Row
        return self._local.connection

    def execute(self, sql: str, params: tuple = ()) -> sqlite3.Cursor:
        """Execute a SQL statement.

        Args:
            sql: SQL statement to execute
            params: Query parameters

        Returns:
            sqlite3 Cursor
        """
        with self._lock:
            try:
                conn = self._get_connection()
                cursor = conn.execute(sql, params)
                return cursor
            except sqlite3.Error as e:
                logger.error(f"Database execute error: {e} | SQL: {sql[:100]}")
                raise DatabaseError(f"Query failed: {e}")

    def execute_many(self, sql: str, params_list: list[tuple]) -> None:
        """Execute a SQL statement with multiple parameter sets.

        Args:
            sql: SQL statement
            params_list: List of parameter tuples
        """
        with self._lock:
            try:
                conn = self._get_connection()
                conn.executemany(sql, params_list)
            except sqlite3.Error as e:
                logger.error(f"Database executemany error: {e}")
                raise DatabaseError(f"Batch query failed: {e}")

    def fetch_one(self, sql: str, params: tuple = ()) -> Optional[dict[str, Any]]:
        """Fetch a single row.

        Args:
            sql: SQL query
            params: Query parameters

        Returns:
            Row dict or None
        """
        cursor = self.execute(sql, params)
        row = cursor.fetchone()
        return dict(row) if row else None

    def fetch_all(self, sql: str, params: tuple = ()) -> list[dict[str, Any]]:
        """Fetch all rows.

        Args:
            sql: SQL query
            params: Query parameters

        Returns:
            List of row dicts
        """
        cursor = self.execute(sql, params)
        return [dict(row) for row in cursor.fetchall()]

    def insert(self, sql: str, params: tuple = ()) -> int:
        """Insert a row and return its row ID.

        Args:
            sql: INSERT statement
            params: Query parameters

        Returns:
            Last inserted row ID
        """
        cursor = self.execute(sql, params)
        return cursor.lastrowid

    def transaction(self, func: Callable) -> Any:
        """Execute a function within a database transaction.

        Args:
            func: Function to execute within transaction

        Returns:
            Function return value
        """
        with self._lock:
            conn = self._get_connection()
            try:
                conn.execute("BEGIN TRANSACTION")
                result = func()
                conn.commit()
                return result
            except Exception as e:
                conn.rollback()
                logger.error(f"Transaction rolled back: {e}")
                raise DatabaseError(f"Transaction failed: {e}")

    def commit(self) -> None:
        """Commit the current transaction."""
        try:
            conn = self._get_connection()
            conn.commit()
        except sqlite3.Error as e:
            logger.error(f"Commit failed: {e}")

    def optimize(self) -> None:
        """Perform database optimization (VACUUM, ANALYZE)."""
        try:
            conn = self._get_connection()
            conn.execute("PRAGMA analysis_limit=400")
            conn.execute("ANALYZE")
            logger.info("Database optimized")
        except sqlite3.Error as e:
            logger.warning(f"Database optimization failed: {e}")

    def get_size(self) -> int:
        """Get database file size in bytes."""
        return self._db_path.stat().st_size if self._db_path.exists() else 0

    def get_table_info(self) -> dict[str, int]:
        """Get row counts for all tables."""
        tables = [
            "users", "sessions", "behavioral_events", "behavioral_features",
            "trusted_features", "datasets", "models", "model_versions",
            "training_history", "authentication_history", "trust_history",
            "risk_history", "enrollment", "assignments", "assignment_progress",
            "audit_logs", "notifications", "backup_history", "cleanup_history",
            "integrity_checks", "configuration"
        ]
        info = {}
        for table in tables:
            try:
                row = self.fetch_one(f"SELECT COUNT(*) as count FROM {table}")
                info[table] = row["count"] if row else 0
            except DatabaseError:
                info[table] = -1
        return info

    def _create_tables(self) -> None:
        """Create all database tables if they don't exist."""
        schema = """
        CREATE TABLE IF NOT EXISTS users (
            user_id TEXT PRIMARY KEY,
            full_name TEXT NOT NULL,
            registration_date TEXT NOT NULL,
            enrollment_status TEXT DEFAULT 'not_started',
            active_model_version TEXT,
            account_status TEXT DEFAULT 'active',
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS sessions (
            session_id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            start_time TEXT NOT NULL,
            end_time TEXT,
            duration_seconds REAL DEFAULT 0,
            authentication_status TEXT DEFAULT 'monitoring',
            average_trust_score REAL DEFAULT 0,
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        );

        CREATE TABLE IF NOT EXISTS behavioral_events (
            event_id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT,
            event_type TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            event_data TEXT,
            FOREIGN KEY (session_id) REFERENCES sessions(session_id)
        );

        CREATE TABLE IF NOT EXISTS behavioral_features (
            feature_id TEXT PRIMARY KEY,
            session_id TEXT,
            timestamp TEXT NOT NULL,
            keyboard_features TEXT,
            mouse_features TEXT,
            scroll_features TEXT,
            session_features TEXT,
            statistical_features TEXT,
            feature_vector TEXT,
            trust_level TEXT DEFAULT 'medium',
            FOREIGN KEY (session_id) REFERENCES sessions(session_id)
        );

        CREATE TABLE IF NOT EXISTS trusted_features (
            trusted_feature_id INTEGER PRIMARY KEY AUTOINCREMENT,
            feature_id TEXT NOT NULL,
            trust_score REAL DEFAULT 0,
            collection_date TEXT NOT NULL,
            retraining_status TEXT DEFAULT 'pending',
            FOREIGN KEY (feature_id) REFERENCES behavioral_features(feature_id)
        );

        CREATE TABLE IF NOT EXISTS datasets (
            dataset_id TEXT PRIMARY KEY,
            dataset_type TEXT NOT NULL,
            creation_date TEXT NOT NULL,
            num_samples INTEGER DEFAULT 0,
            feature_count INTEGER DEFAULT 0,
            dataset_status TEXT DEFAULT 'pending'
        );

        CREATE TABLE IF NOT EXISTS models (
            model_id TEXT PRIMARY KEY,
            model_version TEXT NOT NULL,
            training_date TEXT,
            active_status INTEGER DEFAULT 0,
            validation_status TEXT DEFAULT 'pending',
            file_location TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS model_versions (
            version_id INTEGER PRIMARY KEY AUTOINCREMENT,
            model_id TEXT NOT NULL,
            version_number INTEGER NOT NULL,
            deployment_date TEXT,
            validation_result TEXT,
            rollback_status INTEGER DEFAULT 0,
            FOREIGN KEY (model_id) REFERENCES models(model_id)
        );

        CREATE TABLE IF NOT EXISTS training_history (
            training_id INTEGER PRIMARY KEY AUTOINCREMENT,
            dataset_id TEXT,
            model_version TEXT,
            training_start TEXT,
            training_end TEXT,
            duration_seconds REAL,
            validation_result TEXT,
            FOREIGN KEY (dataset_id) REFERENCES datasets(dataset_id)
        );

        CREATE TABLE IF NOT EXISTS authentication_history (
            auth_id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT,
            timestamp TEXT NOT NULL,
            confidence_score REAL DEFAULT 0,
            trust_score REAL DEFAULT 0,
            auth_result TEXT,
            risk_level TEXT DEFAULT 'low',
            FOREIGN KEY (session_id) REFERENCES sessions(session_id)
        );

        CREATE TABLE IF NOT EXISTS trust_history (
            trust_record_id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT,
            timestamp TEXT NOT NULL,
            trust_score REAL DEFAULT 0,
            trust_category TEXT,
            FOREIGN KEY (session_id) REFERENCES sessions(session_id)
        );

        CREATE TABLE IF NOT EXISTS risk_history (
            risk_id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT,
            timestamp TEXT NOT NULL,
            risk_level TEXT DEFAULT 'low',
            risk_reason TEXT,
            FOREIGN KEY (session_id) REFERENCES sessions(session_id)
        );

        CREATE TABLE IF NOT EXISTS enrollment (
            enrollment_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            start_date TEXT NOT NULL,
            completion_date TEXT,
            current_day INTEGER DEFAULT 1,
            completion_status TEXT DEFAULT 'in_progress',
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        );

        CREATE TABLE IF NOT EXISTS assignments (
            assignment_id TEXT PRIMARY KEY,
            assignment_name TEXT NOT NULL,
            day_number INTEGER NOT NULL,
            duration_minutes INTEGER DEFAULT 20,
            assignment_type TEXT,
            completion_criteria TEXT
        );

        CREATE TABLE IF NOT EXISTS assignment_progress (
            progress_id INTEGER PRIMARY KEY AUTOINCREMENT,
            assignment_id TEXT NOT NULL,
            completion_time TEXT,
            completion_percentage REAL DEFAULT 0,
            validation_status TEXT DEFAULT 'pending',
            FOREIGN KEY (assignment_id) REFERENCES assignments(assignment_id)
        );

        CREATE TABLE IF NOT EXISTS audit_logs (
            log_id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            component TEXT,
            severity TEXT DEFAULT 'information',
            description TEXT,
            metadata TEXT
        );

        CREATE TABLE IF NOT EXISTS notifications (
            notification_id INTEGER PRIMARY KEY AUTOINCREMENT,
            notification_type TEXT NOT NULL,
            message TEXT,
            delivery_time TEXT,
            status TEXT DEFAULT 'pending'
        );

        CREATE TABLE IF NOT EXISTS backup_history (
            backup_id INTEGER PRIMARY KEY AUTOINCREMENT,
            backup_time TEXT NOT NULL,
            backup_size INTEGER DEFAULT 0,
            backup_status TEXT DEFAULT 'pending',
            verification_status TEXT DEFAULT 'pending'
        );

        CREATE TABLE IF NOT EXISTS cleanup_history (
            cleanup_id INTEGER PRIMARY KEY AUTOINCREMENT,
            cleanup_date TEXT NOT NULL,
            records_removed INTEGER DEFAULT 0,
            storage_freed INTEGER DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS integrity_checks (
            check_id INTEGER PRIMARY KEY AUTOINCREMENT,
            check_time TEXT NOT NULL,
            component TEXT,
            result TEXT,
            remarks TEXT
        );

        CREATE TABLE IF NOT EXISTS configuration (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            updated_at TEXT DEFAULT (datetime('now'))
        );

        -- Indexes
        CREATE INDEX IF NOT EXISTS idx_sessions_user ON sessions(user_id);
        CREATE INDEX IF NOT EXISTS idx_features_session ON behavioral_features(session_id);
        CREATE INDEX IF NOT EXISTS idx_features_timestamp ON behavioral_features(timestamp);
        CREATE INDEX IF NOT EXISTS idx_auth_session ON authentication_history(session_id);
        CREATE INDEX IF NOT EXISTS idx_auth_timestamp ON authentication_history(timestamp);
        CREATE INDEX IF NOT EXISTS idx_trust_session ON trust_history(session_id);
        CREATE INDEX IF NOT EXISTS idx_risk_session ON risk_history(session_id);
        CREATE INDEX IF NOT EXISTS idx_events_session ON behavioral_events(session_id);
        CREATE INDEX IF NOT EXISTS idx_events_type ON behavioral_events(event_type);
        CREATE INDEX IF NOT EXISTS idx_audit_severity ON audit_logs(severity);
        CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON audit_logs(timestamp);
        CREATE INDEX IF NOT EXISTS idx_models_active ON models(active_status);
        CREATE INDEX IF NOT EXISTS idx_models_version ON models(model_version);
        """
        conn = self._get_connection()
        conn.executescript(schema)
        conn.commit()

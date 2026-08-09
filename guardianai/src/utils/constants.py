"""Application-wide constants, enums, and default configuration values."""

import enum
import os
from pathlib import Path


# ─── Application Paths ────────────────────────────────────────────────────────

APP_NAME = "GuardianAI"
APP_VERSION = "1.0.0"
APP_AUTHOR = "GuardianAI"

# Base data directory (user-local)
_DATA_DIR = Path(os.environ.get(
    "GUARDIANAI_DATA_DIR",
    Path.home() / f".{APP_NAME.lower()}"
))

DB_PATH = _DATA_DIR / "guardianai.db"
CONFIG_PATH = _DATA_DIR / "config.enc"
MODELS_DIR = _DATA_DIR / "models"
BACKUPS_DIR = _DATA_DIR / "backups"
LOGS_DIR = _DATA_DIR / "logs"
TEMP_DIR = _DATA_DIR / "temp"

# Ensure directories exist
for _p in [MODELS_DIR, BACKUPS_DIR, LOGS_DIR, TEMP_DIR]:
    _p.mkdir(parents=True, exist_ok=True)


# ─── Enrollment ───────────────────────────────────────────────────────────────

ENROLLMENT_DAYS = 7
ENROLLMENT_DAILY_DURATION_MIN = 20  # minimum minutes per daily assignment
ENROLLMENT_REQUIRED_SESSIONS = 7    # minimum behavioral sessions required (7 days OR 7 sessions)


# ─── Behavioral Monitoring ────────────────────────────────────────────────────

BEHAVIORAL_WINDOW_SECONDS = 60       # aggregation window size (seconds)
BEHAVIORAL_WINDOW_OVERLAP = 0        # overlap between windows (seconds)
EVENT_BUFFER_MAX_SIZE = 10000        # max events in in-memory buffer
EVENT_BUFFER_FLUSH_INTERVAL = 5.0    # flush interval (seconds)
IDLE_THRESHOLD_SECONDS = 300         # 5 minutes without activity = idle
ACTIVITY_TIMEOUT_SECONDS = 30        # consider user away after 30s inactivity


# ─── Machine Learning ─────────────────────────────────────────────────────────

DEFAULT_TRAIN_TEST_SPLIT = 0.2
DEFAULT_VALIDATION_SPLIT = 0.1
RANDOM_STATE = 42

# Anomaly detection / isolation forest
ANOMALY_CONTAMINATION = 0.1
ANOMALY_N_ESTIMATORS = 100

# Trust scoring
TRUST_WINDOW_SIZE = 50               # number of recent predictions to use
TRUST_HIGH_THRESHOLD = 0.8
TRUST_MEDIUM_THRESHOLD = 0.5
TRUST_LOW_THRESHOLD = 0.0

# Confidence smoothing
CONFIDENCE_ALPHA = 0.3               # EMA smoothing factor

# Risk levels
RISK_LOW = 0.0
RISK_MEDIUM = 0.3
RISK_HIGH = 0.6
RISK_CRITICAL = 0.8

# Retraining
RETRAINING_INTERVAL_DAYS = 30
RETRAINING_MIN_SAMPLES = 100
SLIDING_WINDOW_DAYS = 90             # keep 90 days of trusted data
SLIDING_WINDOW_MAX_SAMPLES = 10000

# Model validation
MIN_ACCEPTABLE_ACCURACY = 0.85
MIN_ACCEPTABLE_F1 = 0.80
MAX_ACCEPTABLE_FAR = 0.10            # false acceptance rate
MAX_ACCEPTABLE_FRR = 0.15            # false rejection rate


# ─── Security ─────────────────────────────────────────────────────────────────

ENCRYPTION_ALGORITHM = "AES-256-GCM"
KEY_DERIVATION_ITERATIONS = 100_000
BACKUP_RETENTION_DAYS = 30
BACKUP_INTERVAL_HOURS = 24
CLEANUP_INTERVAL_HOURS = 72
INTEGRITY_CHECK_INTERVAL_HOURS = 24

# Logging
LOG_MAX_BYTES = 10 * 1024 * 1024     # 10 MB
LOG_BACKUP_COUNT = 5
LOG_LEVEL = "INFO"

# ─── Feature Definitions ──────────────────────────────────────────────────────

# Total number of features in each feature vector
NUM_KEYBOARD_FEATURES = 12
NUM_MOUSE_FEATURES = 10
NUM_SCROLL_FEATURES = 6
NUM_SESSION_FEATURES = 6
NUM_DERIVED_FEATURES = 8
TOTAL_FEATURES = (NUM_KEYBOARD_FEATURES + NUM_MOUSE_FEATURES +
                  NUM_SCROLL_FEATURES + NUM_SESSION_FEATURES +
                  NUM_DERIVED_FEATURES)

# ─── Thread Names ─────────────────────────────────────────────────────────────

THREAD_UI = "UI-Thread"
THREAD_BEHAVIOR = "Behavior-Collection-Thread"
THREAD_FEATURE = "Feature-Processing-Thread"
THREAD_AUTH = "Authentication-Thread"
THREAD_DB = "Database-Thread"
THREAD_MAINTENANCE = "Maintenance-Thread"


# ─── Enums ────────────────────────────────────────────────────────────────────

class AuthStatus(enum.Enum):
    """Authentication status values."""
    AUTHENTICATED = "authenticated"
    MONITORING = "monitoring"
    DEGRADED = "degraded"
    LOCKED = "locked"
    UNAVAILABLE = "unavailable"


class TrustLevel(enum.Enum):
    """Trust level categories."""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class RiskLevel(enum.Enum):
    """Risk level categories."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class EventType(enum.Enum):
    """Types of behavioral events."""
    KEY_PRESS = "key_press"
    KEY_RELEASE = "key_release"
    MOUSE_MOVE = "mouse_move"
    MOUSE_CLICK = "mouse_click"
    MOUSE_DRAG = "mouse_drag"
    SCROLL = "scroll"
    IDLE = "idle"
    ACTIVE = "active"


class EnrollmentStatus(enum.Enum):
    """Enrollment status values."""
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class ModelStatus(enum.Enum):
    """Model lifecycle status values."""
    TRAINING = "training"
    VALIDATION = "validation"
    PRODUCTION = "production"
    ARCHIVED = "archived"
    ROLLBACK = "rollback"
    FAILED = "failed"


class DatasetType(enum.Enum):
    """Dataset type classification."""
    ENROLLMENT = "enrollment"
    TRAINING = "training"
    VALIDATION = "validation"
    RETRAINING = "retraining"
    PRODUCTION = "production"


class SecurityEvent(enum.Enum):
    """Security event severity levels."""
    INFORMATION = "information"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"

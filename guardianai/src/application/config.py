"""Configuration Manager - Centralized configuration management with encryption.

Loads, validates, saves, and manages application configuration with secure
encrypted storage for sensitive values.
"""

import json
import copy
import logging
from pathlib import Path
from typing import Any, Optional
from datetime import datetime

from src.utils.constants import CONFIG_PATH, APP_NAME, APP_VERSION
from src.security.encryption import EncryptionManager
from src.security.secure_storage import SecureStorageManager

logger = logging.getLogger(__name__)

_DEFAULT_CONFIG: dict[str, Any] = {
    # Application
    "app": {
        "name": APP_NAME,
        "version": APP_VERSION,
        "language": "en",
        "theme": "dark",
        "auto_start": True,
        "minimize_to_tray": True,
        "notifications_enabled": True,
    },
    # Authentication
    "auth": {
        "sensitivity": 0.5,          # 0.0 (low) to 1.0 (high)
        "trust_threshold": 0.7,
        "risk_threshold": 0.6,
        "lock_on_critical_risk": True,
        "reauthenticate_days": 0,    # 0 = never require re-auth
    },
    # Monitoring
    "monitoring": {
        "window_seconds": 60,
        "idle_threshold_seconds": 300,
        "collect_keyboard": True,
        "collect_mouse": True,
        "collect_scroll": True,
    },
    # Training
    "training": {
        "retraining_interval_days": 30,
        "retraining_min_samples": 100,
        "sliding_window_days": 90,
        "sliding_window_max_samples": 10000,
        "min_accuracy": 0.85,
        "min_f1": 0.80,
        "max_far": 0.10,
        "max_frr": 0.15,
    },
    # Privacy
    "privacy": {
        "data_retention_days": 365,
        "keep_raw_events": False,
        "anonymize_features": True,
    },
    # Maintenance
    "maintenance": {
        "backup_interval_hours": 24,
        "backup_retention_days": 30,
        "cleanup_interval_hours": 72,
        "integrity_check_interval_hours": 24,
        "log_level": "INFO",
        "log_max_bytes": 10485760,
        "log_backup_count": 5,
    },
}


class ConfigurationError(Exception):
    """Raised when configuration operations fail."""
    pass


class ConfigValidationError(ConfigurationError):
    """Raised when configuration validation fails."""
    pass


class ConfigurationManager:
    """Centralized configuration manager with encrypted storage."""

    def __init__(self) -> None:
        self._config: dict[str, Any] = {}
        self._encryption: Optional[EncryptionManager] = None
        self._secure_storage: Optional[SecureStorageManager] = None
        self._loaded = False

    @property
    def is_loaded(self) -> bool:
        return self._loaded

    def initialize(
        self,
        encryption: EncryptionManager,
        secure_storage: SecureStorageManager,
    ) -> None:
        """Initialize with security dependencies."""
        self._encryption = encryption
        self._secure_storage = secure_storage

    def load(self) -> dict[str, Any]:
        """Load configuration from encrypted file or create defaults."""
        if CONFIG_PATH.exists():
            try:
                encrypted_data = CONFIG_PATH.read_bytes()
                if self._encryption:
                    decrypted = self._encryption.decrypt(encrypted_data)
                else:
                    # Fallback: try reading as JSON directly
                    decrypted = CONFIG_PATH.read_text()
                self._config = json.loads(decrypted)
                self._validate_config()
                logger.info("Configuration loaded successfully")
            except (json.JSONDecodeError, KeyError, Exception) as e:
                logger.warning(f"Failed to load config, using defaults: {e}")
                self._config = copy.deepcopy(_DEFAULT_CONFIG)
                self._save()
        else:
            logger.info("No config file found, creating with defaults")
            self._config = copy.deepcopy(_DEFAULT_CONFIG)
            self._save()

        self._loaded = True
        return self.get_all()

    def get(self, key: str, default: Any = None) -> Any:
        """Get a configuration value using dot-notation key.

        Args:
            key: Dot-notation path (e.g., 'auth.sensitivity')
            default: Default value if key not found

        Returns:
            Configuration value or default
        """
        parts = key.split(".")
        value = self._config
        try:
            for part in parts:
                value = value[part]
            return value
        except (KeyError, TypeError):
            return default

    def set(self, key: str, value: Any) -> None:
        """Set a configuration value and persist.

        Args:
            key: Dot-notation path (e.g., 'auth.sensitivity')
            value: Value to set
        """
        parts = key.split(".")
        target = self._config
        for part in parts[:-1]:
            if part not in target:
                target[part] = {}
            target = target[part]
        target[parts[-1]] = value
        self._save()

    def get_all(self) -> dict[str, Any]:
        """Get a deep copy of the entire configuration."""
        return copy.deepcopy(self._config)

    def update(self, updates: dict[str, Any]) -> None:
        """Update multiple configuration values at once.

        Args:
            updates: Dictionary of dot-notation keys to values
        """
        for key, value in updates.items():
            self.set(key, value)

    def restore_defaults(self) -> None:
        """Restore all configuration values to defaults."""
        self._config = copy.deepcopy(_DEFAULT_CONFIG)
        self._save()
        logger.info("Configuration restored to defaults")

    def export_config(self) -> str:
        """Export configuration as JSON string."""
        return json.dumps(self._config, indent=2)

    def import_config(self, json_str: str) -> None:
        """Import configuration from JSON string."""
        try:
            imported = json.loads(json_str)
            self._validate_dict(imported)
            self._config = imported
            self._save()
            logger.info("Configuration imported successfully")
        except (json.JSONDecodeError, ConfigValidationError) as e:
            raise ConfigValidationError(f"Invalid configuration: {e}")

    def _validate_config(self) -> None:
        """Validate the current configuration."""
        self._validate_dict(self._config)

    def _validate_dict(self, config: dict) -> None:
        """Validate configuration dictionary structure."""
        required_keys = ["app", "auth", "monitoring", "training",
                         "privacy", "maintenance"]
        for key in required_keys:
            if key not in config:
                raise ConfigValidationError(f"Missing required section: {key}")

        # Validate specific value ranges
        auth = config.get("auth", {})
        sens = auth.get("sensitivity", 0.5)
        if not 0.0 <= sens <= 1.0:
            raise ConfigValidationError(
                f"auth.sensitivity must be 0.0-1.0, got {sens}"
            )

        trust = auth.get("trust_threshold", 0.7)
        if not 0.0 <= trust <= 1.0:
            raise ConfigValidationError(
                f"auth.trust_threshold must be 0.0-1.0, got {trust}"
            )

    def _save(self) -> None:
        """Persist configuration to encrypted file."""
        try:
            json_str = json.dumps(self._config, indent=2)
            if self._encryption:
                encrypted = self._encryption.encrypt(json_str.encode())
                CONFIG_PATH.write_bytes(encrypted)
            else:
                CONFIG_PATH.write_text(json_str)
            logger.debug("Configuration saved")
        except Exception as e:
            raise ConfigurationError(f"Failed to save configuration: {e}")

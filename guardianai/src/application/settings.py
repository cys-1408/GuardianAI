"""Settings Manager - Manages user-configurable application settings.

Provides validation, persistence, and change notification for all
user-facing settings across the application.
"""

import logging
from typing import Any, Optional

from src.application.config import ConfigurationManager, ConfigValidationError

logger = logging.getLogger(__name__)


class SettingsManager:
    """Centralized settings management with validation."""

    def __init__(self, config_manager: ConfigurationManager) -> None:
        self._config = config_manager
        self._settings_cache: dict[str, Any] = {}
        self._refresh_cache()

    def _refresh_cache(self) -> None:
        """Refresh the internal settings cache from configuration."""
        self._settings_cache = self._config.get_all()

    def get(self, key: str, default: Any = None) -> Any:
        """Get a setting value.

        Args:
            key: Dot-notation path (e.g., 'auth.sensitivity')
            default: Default value if not found

        Returns:
            Setting value
        """
        return self._config.get(key, default)

    def set(self, key: str, value: Any) -> bool:
        """Set a setting value with validation.

        Args:
            key: Dot-notation path
            value: Value to set

        Returns:
            True if setting was applied successfully
        """
        if self._validate(key, value):
            self._config.set(key, value)
            self._refresh_cache()
            logger.info(f"Setting updated: {key} = {value}")
            return True
        return False

    def set_batch(self, settings: dict[str, Any]) -> dict[str, bool]:
        """Set multiple settings at once.

        Args:
            settings: Dict of key->value pairs

        Returns:
            Dict of key->success status
        """
        results = {}
        for key, value in settings.items():
            results[key] = self.set(key, value)
        return results

    def _validate(self, key: str, value: Any) -> bool:
        """Validate a setting value before applying.

        Args:
            key: Setting key path
            value: Proposed value

        Returns:
            True if valid
        """
        validators = {
            "auth.sensitivity": self._validate_range_0_1,
            "auth.trust_threshold": self._validate_range_0_1,
            "auth.risk_threshold": self._validate_range_0_1,
            "training.retraining_interval_days": self._validate_positive_int,
            "training.retraining_min_samples": self._validate_positive_int,
            "training.sliding_window_days": self._validate_positive_int,
            "monitoring.window_seconds": self._validate_positive_int,
            "monitoring.idle_threshold_seconds": self._validate_positive_int,
            "privacy.data_retention_days": self._validate_positive_int,
            "maintenance.backup_interval_hours": self._validate_positive_int,
            "maintenance.backup_retention_days": self._validate_positive_int,
        }

        validator = validators.get(key)
        if validator and not validator(value):
            logger.warning(f"Validation failed for {key}: {value}")
            return False
        return True

    @staticmethod
    def _validate_range_0_1(value: Any) -> bool:
        """Validate value is a number between 0 and 1."""
        return isinstance(value, (int, float)) and 0.0 <= value <= 1.0

    @staticmethod
    def _validate_positive_int(value: Any) -> bool:
        """Validate value is a positive integer."""
        return isinstance(value, int) and value > 0

    @staticmethod
    def _validate_bool(value: Any) -> bool:
        """Validate value is a boolean."""
        return isinstance(value, bool)

    def restore_defaults(self) -> None:
        """Restore all settings to factory defaults."""
        self._config.restore_defaults()
        self._refresh_cache()
        logger.info("Settings restored to defaults")

    def export_settings(self) -> str:
        """Export current settings as JSON string."""
        return self._config.export_config()

    def import_settings(self, json_str: str) -> bool:
        """Import settings from JSON string.

        Args:
            json_str: JSON configuration string

        Returns:
            True if import succeeded
        """
        try:
            self._config.import_config(json_str)
            self._refresh_cache()
            logger.info("Settings imported successfully")
            return True
        except ConfigValidationError as e:
            logger.error(f"Settings import failed: {e}")
            return False

    def get_all(self) -> dict[str, Any]:
        """Get all settings as a dictionary."""
        return self._settings_cache

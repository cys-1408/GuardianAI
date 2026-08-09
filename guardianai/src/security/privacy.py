"""Privacy Manager - Enforces privacy policies throughout the application.

Ensures behavioral information remains under the user's complete control by
validating every request involving behavioral data before granting access.
"""

import logging
from typing import Any, Optional

from src.application.config import ConfigurationManager

logger = logging.getLogger(__name__)


class PrivacyManager:
    """Enforces privacy policies and controls access to behavioral data."""

    def __init__(self, config: ConfigurationManager) -> None:
        self._config = config
        self._privacy_policies: dict[str, bool] = {
            "allow_behavior_collection": True,
            "allow_authentication": True,
            "allow_adaptive_learning": True,
            "allow_data_deletion": True,
            "allow_data_export": True,
        }

    def check_access(self, resource: str, action: str) -> bool:
        """Check if access to a resource is allowed.

        Args:
            resource: Resource being accessed (e.g., 'behavioral_data')
            action: Action being performed (e.g., 'read', 'delete')

        Returns:
            True if access is permitted
        """
        policies = {
            ("behavioral_data", "collect"): self._privacy_policies.get(
                "allow_behavior_collection", True
            ),
            ("behavioral_data", "read"): True,
            ("behavioral_data", "delete"): self._privacy_policies.get(
                "allow_data_deletion", True
            ),
            ("behavioral_data", "export"): self._privacy_policies.get(
                "allow_data_export", True
            ),
            ("authentication_data", "read"): True,
            ("authentication_data", "delete"): self._privacy_policies.get(
                "allow_data_deletion", True
            ),
            ("model_data", "train"): True,
            ("model_data", "read"): True,
        }
        return policies.get((resource, action), False)

    def is_collection_allowed(self) -> bool:
        """Check if behavioral data collection is currently allowed."""
        return self._privacy_policies.get("allow_behavior_collection", True)

    def set_policy(self, policy: str, value: bool) -> None:
        """Set a privacy policy value.

        Args:
            policy: Policy name
            value: Policy value
        """
        if policy in self._privacy_policies:
            self._privacy_policies[policy] = value
            logger.info(f"Privacy policy '{policy}' set to {value}")

    def get_enforcement_status(self) -> dict[str, Any]:
        """Get current privacy enforcement status."""
        return {
            "policies": dict(self._privacy_policies),
            "data_retention_days": self._config.get("privacy.data_retention_days", 365),
            "keep_raw_events": self._config.get("privacy.keep_raw_events", False),
            "anonymize_features": self._config.get("privacy.anonymize_features", True),
        }

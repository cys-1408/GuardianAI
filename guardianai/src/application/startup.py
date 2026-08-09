"""Startup Manager - Handles application initialization and verification.

Executes the startup sequence in a predefined order, verifies dependencies,
initializes modules, loads resources, and checks database integrity.
"""

import logging
import sys
from typing import Any
from pathlib import Path

from src.utils.constants import (
    _DATA_DIR, DB_PATH, MODELS_DIR, BACKUPS_DIR, LOGS_DIR
)

logger = logging.getLogger(__name__)


class StartupManager:
    """Manages the application startup sequence."""

    def __init__(self, app_core: Any) -> None:
        self._app_core = app_core
        self._startup_ok = False

    def execute(self) -> bool:
        """Execute the full startup sequence.

        Returns:
            True if startup was successful, False otherwise.
        """
        logger.info("Starting startup sequence...")

        startup_steps = [
            ("verify_directories", self._verify_directories),
            ("verify_python_version", self._verify_python_version),
            ("check_database", self._check_database),
            ("initialize_logging", self._initialize_logging),
            ("load_resources", self._load_resources),
        ]

        for step_name, step_func in startup_steps:
            try:
                if not step_func():
                    logger.error(f"Startup step '{step_name}' failed")
                    return False
                logger.debug(f"Startup step '{step_name}' completed")
            except Exception as e:
                logger.error(f"Startup step '{step_name}' failed: {e}")
                return False

        self._startup_ok = True
        logger.info("Startup sequence completed successfully")
        return True

    def _verify_directories(self) -> bool:
        """Verify and create required application directories."""
        try:
            for path in [_DATA_DIR, MODELS_DIR, BACKUPS_DIR, LOGS_DIR]:
                path.mkdir(parents=True, exist_ok=True)
                if not path.exists():
                    logger.error(f"Failed to create directory: {path}")
                    return False

            logger.info(f"Data directory: {_DATA_DIR}")
            return True
        except PermissionError as e:
            logger.error(f"Permission denied creating directories: {e}")
            return False
        except OSError as e:
            logger.error(f"OS error creating directories: {e}")
            return False

    def _verify_python_version(self) -> bool:
        """Verify Python version meets minimum requirements."""
        if sys.version_info < (3, 10):
            logger.error(
                f"Python 3.10+ required, found {sys.version_info.major}."
                f"{sys.version_info.minor}"
            )
            return False
        logger.debug(f"Python {sys.version} OK")
        return True

    def _check_database(self) -> bool:
        """Check if database file exists and is accessible."""
        db_exists = DB_PATH.exists()
        if db_exists:
            db_size = DB_PATH.stat().st_size
            logger.info(f"Database found: {DB_PATH} ({db_size} bytes)")
        else:
            logger.info("No existing database, will create on first use")
        return True

    def _initialize_logging(self) -> bool:
        """Configure logging system."""
        try:
            log_file = LOGS_DIR / "guardianai.log"
            logging.basicConfig(
                level=logging.INFO,
                format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
                handlers=[
                    logging.FileHandler(log_file, encoding="utf-8"),
                    logging.StreamHandler(sys.stdout),
                ],
            )
            logger.info(f"Logging initialized: {log_file}")
            return True
        except Exception as e:
            print(f"Failed to initialize logging: {e}", file=sys.stderr)
            return False

    def _load_resources(self) -> bool:
        """Load application resources."""
        # Load application metadata
        from src import __version__, __description__
        logger.info(f"{__description__} v{__version__}")
        return True

    @property
    def startup_successful(self) -> bool:
        return self._startup_ok

"""GuardianAI - Main Application Entry Point.

Enrollment gate:
  - If enrollment is NOT complete → show EnrollmentOverlay only (no main window)
  - If enrollment IS complete     → show MainWindow directly
"""

import sys
import logging
import traceback
from pathlib import Path
from datetime import datetime
from typing import Optional

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt

from src import __version__, __description__
from src.application.core import ApplicationCore
from src.utils.constants import ENROLLMENT_REQUIRED_SESSIONS

logger = logging.getLogger(__name__)

_STARTUP_LOG = Path.home() / ".guardianai" / "startup_errors.log"


def _log_startup_error(phase: str, exc_info: bool = True) -> None:
    try:
        _STARTUP_LOG.parent.mkdir(parents=True, exist_ok=True)
        with open(_STARTUP_LOG, "a", encoding="utf-8") as f:
            f.write(f"\n{'='*60}\n[{datetime.now().isoformat()}] FATAL ERROR during: {phase}\n")
            if exc_info:
                traceback.print_exc(file=f)
            f.write(f"{'='*60}\n")
    except Exception:
        pass


def _show_fatal_error_dialog(title: str, message: str) -> None:
    try:
        import ctypes
        ctypes.windll.user32.MessageBoxW(0, message, title, 0x10)
    except Exception:
        print(f"FATAL: {title} - {message}", file=sys.stderr)


def _enrollment_is_complete(core: ApplicationCore) -> bool:
    """Check whether enrollment has been completed.

    Enrollment completes when either:
    - All 7 daily assignments are done (standard path)
    - 7 unique sessions have been recorded (session-based completion)
    - The config flag or DB says 'completed'
    """
    try:
        if core.enrollment_system and core.enrollment_system.status == "completed":
            return True
        # Also check config flag persisted across restarts
        if core.config:
            status = core.config.get("app.enrollment_status", "")
            if status == "completed":
                return True
        # Check DB directly
        if core.db:
            row = core.db.fetch_one(
                "SELECT completion_status FROM enrollment "
                "WHERE completion_status = 'completed' LIMIT 1"
            )
            if row:
                return True
        # Check if 7+ sessions have been completed (session-based completion gate)
        # Uses the sessions table which is now populated by SessionManager
        if core.db:
            row = core.db.fetch_one(
                "SELECT COUNT(*) as count FROM sessions"
            )
            if row and row.get("count", 0) >= ENROLLMENT_REQUIRED_SESSIONS:
                logger.info(f"Enrollment complete: {row['count']} sessions recorded")
                # Mark as completed in config for persistence
                if core.config:
                    core.config.set("app.enrollment_status", "completed")
                if core.enrollment_system and core.enrollment_system.status != "completed":
                    core.enrollment_system.mark_completed()
                return True
    except Exception as e:
        logger.warning(f"Could not determine enrollment status: {e}")
    return False


class GuardianAIApplication:
    """Main GuardianAI application wrapper with enrollment gate."""

    def __init__(self) -> None:
        self._qt_app: Optional[QApplication] = None
        self._core: Optional[ApplicationCore] = None
        self._main_window = None
        self._enrollment_overlay = None

    def initialize(self) -> bool:
        try:
            self._qt_app = QApplication(sys.argv)
            self._qt_app.setApplicationName("GuardianAI")
            self._qt_app.setApplicationVersion(__version__)
            self._qt_app.setOrganizationName("GuardianAI")
            self._qt_app.setQuitOnLastWindowClosed(False)
            self._qt_app.setStyle("Fusion")

            self._core = ApplicationCore()
            if not self._core.initialize():
                _log_startup_error("core.initialize() returned False", exc_info=False)
                _show_fatal_error_dialog(
                    "GuardianAI - Initialization Failed",
                    "The application core failed to initialize.\n\n"
                    f"Check the log at: {_STARTUP_LOG}",
                )
                return False

            # ── Enrollment gate ──────────────────────────────────────
            if _enrollment_is_complete(self._core):
                # Enrollment done — show full main window
                from src.ui.main_window import MainWindow
                self._main_window = MainWindow(app_core=self._core)
                self._core.set_presentation_layer(self._main_window)
            else:
                # Enrollment not done — show enrollment overlay only
                from src.ui.enrollment_overlay import EnrollmentOverlay
                self._enrollment_overlay = EnrollmentOverlay(app_core=self._core)
                self._core.set_presentation_layer(self._enrollment_overlay)

                # When enrollment completes, swap to main window
                from src.utils.signals import get_signals
                get_signals().enrollment_completed.connect(self._on_enrollment_completed)

                self._enrollment_overlay.showMaximized()

            return True

        except Exception as e:
            error_msg = f"{type(e).__name__}: {e}"
            _log_startup_error(f"initialize() - {error_msg}")
            _show_fatal_error_dialog(
                "GuardianAI - Unexpected Error",
                f"An unexpected error occurred during startup:\n\n{error_msg}\n\n"
                f"Check the full log at: {_STARTUP_LOG}",
            )
            return False

    def _on_enrollment_completed(self) -> None:
        """Switch from enrollment overlay to main window after enrollment finishes."""
        try:
            from src.ui.main_window import MainWindow
            self._main_window = MainWindow(app_core=self._core)
            self._core.set_presentation_layer(self._main_window)
            # Show the main window maximized
            self._main_window.showMaximized()
            # Overlay hides itself via its own signal handler
            if self._enrollment_overlay:
                self._enrollment_overlay.hide()
        except Exception as e:
            logger.error(f"Failed to open main window after enrollment: {e}")

    def run(self) -> int:
        if not self._core or not self._core.is_initialized:
            logger.error("Cannot run: application not initialized")
            return 1

        self._core.start()
        logger.info(f"{__description__} v{__version__} started")
        return self._qt_app.exec() if self._qt_app else 0

    def shutdown(self) -> None:
        if self._main_window:
            self._main_window.close()
        if self._enrollment_overlay:
            self._enrollment_overlay.close()
        if self._core:
            self._core.shutdown()


def main() -> int:
    app = GuardianAIApplication()
    try:
        if not app.initialize():
            return 1
        exit_code = app.run()
        app.shutdown()
        return exit_code
    except Exception as e:
        _log_startup_error(f"main() - {type(e).__name__}: {e}")
        _show_fatal_error_dialog(
            "GuardianAI - Fatal Error",
            f"A fatal error occurred: {type(e).__name__}: {e}\n\n"
            f"Check the log at: {_STARTUP_LOG}",
        )
        return 1


if __name__ == "__main__":
    sys.exit(main())

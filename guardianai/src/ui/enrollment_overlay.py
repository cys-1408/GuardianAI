"""Enrollment Overlay — shown exclusively during the 7-day enrollment period.

Full main window is hidden until enrollment completes. The overlay uses
the GuardianAI design-system theme while keeping the same class API.
"""

from __future__ import annotations

import logging
from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import (
    QColor, QPainter, QFont, QPixmap, QIcon,
)
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QProgressBar, QGraphicsDropShadowEffect,
    QScrollArea, QApplication, QSystemTrayIcon, QMenu,
)

from src.utils.signals import get_signals
from src.utils.constants import ENROLLMENT_DAYS, APP_NAME
from src.ui.enrollment_wizard import EnrollmentWizardWidget
from src.ui.theme import (
    with_alpha,
    BG, PANEL, CARD, PRIMARY, AI, SUCCESS, WARNING, CRITICAL, MUTED,
    TEXT_PRI, TEXT_SEC, TEXT_DIM, BORDER, BORDER_STRONG,
)

logger = logging.getLogger(__name__)


class EnrollmentOverlay(QWidget):
    """Full-screen enrollment overlay shown during the 7-day enrollment period."""

    def __init__(self, app_core=None):
        super().__init__()
        self._app_core = app_core
        self._signals = get_signals()
        self._completed_days = 0
        self._tray: Optional[QSystemTrayIcon] = None

        self._setup_window()
        self._setup_ui()
        self._setup_tray()
        self._connect_signals()

    def _setup_window(self):
        self.setWindowTitle(f"{APP_NAME} — Enrollment")
        self.setWindowFlags(Qt.Window | Qt.WindowMinimizeButtonHint | Qt.WindowCloseButtonHint)
        self.setMinimumSize(1100, 750)
        self.setStyleSheet(f"""
            QWidget {{
                background: {BG};
                color: {TEXT_PRI};
                font-family: 'Segoe UI', -apple-system, sans-serif;
            }}
            QScrollBar:vertical {{
                background: transparent;
                width: 6px;
                border-radius: 3px;
            }}
            QScrollBar::handle:vertical {{
                background: #2A3440;
                border-radius: 3px;
                min-height: 30px;
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
            QToolTip {{
                background: #1A212B;
                color: {TEXT_PRI};
                border: 1px solid {BORDER_STRONG};
                padding: 6px 10px;
                border-radius: 6px;
            }}
        """)

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Top header bar ──────────────────────────────────────────
        header = QFrame()
        header.setFixedHeight(64)
        header.setStyleSheet(f"""
            QFrame {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #0D1117, stop:0.5 #0A0D12, stop:1 #0D1117);
                border-bottom: 1px solid {BORDER};
            }}
        """)
        h_layout = QHBoxLayout(header)
        h_layout.setContentsMargins(28, 0, 28, 0)

        logo_lbl = QLabel("🛡")
        logo_lbl.setStyleSheet(f"font-size: 20px; color: {PRIMARY}; background: transparent;")
        h_layout.addWidget(logo_lbl)

        name_lbl = QLabel(APP_NAME)
        name_lbl.setStyleSheet(
            f"font-size: 18px; font-weight: 700; color: {TEXT_PRI}; "
            f"background: transparent; letter-spacing: 2px; margin-left: 6px;"
        )
        h_layout.addWidget(name_lbl)

        phase_lbl = QLabel("  ·  Behavioral Enrollment")
        phase_lbl.setStyleSheet(f"font-size: 13px; color: {TEXT_DIM}; background: transparent;")
        h_layout.addWidget(phase_lbl)

        h_layout.addStretch()

        self._header_badge = QLabel("Day 0 / 7")
        self._header_badge.setStyleSheet(f"""
            QLabel {{
                background: {with_alpha(AI, '22')};
                color: {AI};
                padding: 5px 16px;
                border-radius: 14px;
                font-size: 12px;
                font-weight: bold;
                border: 1px solid {with_alpha(AI, '44')};
            }}
        """)
        h_layout.addWidget(self._header_badge)

        root.addWidget(header)

        # ── Progress strip ──────────────────────────────────────────
        prog_strip = QFrame()
        prog_strip.setFixedHeight(4)
        prog_strip.setStyleSheet("background: #0A0D12;")
        prog_layout = QHBoxLayout(prog_strip)
        prog_layout.setContentsMargins(0, 0, 0, 0)
        self._top_progress = QProgressBar()
        self._top_progress.setRange(0, 100)
        self._top_progress.setValue(0)
        self._top_progress.setTextVisible(False)
        self._top_progress.setFixedHeight(4)
        self._top_progress.setStyleSheet("""
            QProgressBar { background: #0A0D12; border: none; border-radius: 0; }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #7C4DFF, stop:0.5 #00D4FF, stop:1 #00E676);
                border-radius: 0;
            }
        """)
        prog_layout.addWidget(self._top_progress)
        root.addWidget(prog_strip)

        # ── Main content ────────────────────────────────────────────
        self._wizard = EnrollmentWizardWidget()
        root.addWidget(self._wizard, 1)

        # ── Bottom status bar ───────────────────────────────────────
        status_bar = QFrame()
        status_bar.setFixedHeight(36)
        status_bar.setStyleSheet(f"""
            QFrame {{
                background: #0A0D12;
                border-top: 1px solid {BORDER};
            }}
        """)
        sb_layout = QHBoxLayout(status_bar)
        sb_layout.setContentsMargins(20, 0, 20, 0)

        self._status_lbl = QLabel("⚡  Behavioral monitoring active — data is being collected")
        self._status_lbl.setStyleSheet(f"font-size: 11px; color: {TEXT_DIM}; background: transparent;")
        sb_layout.addWidget(self._status_lbl)
        sb_layout.addStretch()

        privacy_lbl = QLabel("🔒  All data stays on your device")
        privacy_lbl.setStyleSheet(f"font-size: 11px; color: {TEXT_DIM}; background: transparent;")
        sb_layout.addWidget(privacy_lbl)

        root.addWidget(status_bar)

    def _setup_tray(self):
        """Setup system tray so user can minimize and restore."""
        self._tray = QSystemTrayIcon(self)
        px = QPixmap(32, 32)
        px.fill(Qt.transparent)
        p = QPainter(px)
        p.setRenderHint(QPainter.Antialiasing)
        p.setBrush(QColor(PRIMARY))
        p.setPen(Qt.NoPen)
        p.drawRoundedRect(2, 4, 28, 24, 6, 6)
        p.setBrush(QColor("#04121A"))
        p.setFont(QFont("Segoe UI", 14, QFont.Bold))
        p.drawText(px.rect(), Qt.AlignCenter, "G")
        p.end()
        self._tray.setIcon(QIcon(px))
        self._tray.setToolTip(f"{APP_NAME} — Enrollment in progress")

        menu = QMenu()
        menu.setStyleSheet(f"""
            QMenu {{ background: #12161D; color: {TEXT_PRI}; border: 1px solid {BORDER_STRONG};
                    padding: 6px; border-radius: 8px; }}
            QMenu::item {{ padding: 8px 24px; border-radius: 4px; }}
            QMenu::item:selected {{ background: {with_alpha(PRIMARY, '22')}; }}
        """)
        open_act = menu.addAction("✦  Open Enrollment")
        open_act.triggered.connect(self._show_and_raise)
        menu.addSeparator()
        quit_act = menu.addAction("✕  Exit")
        quit_act.triggered.connect(self._quit)

        self._tray.setContextMenu(menu)
        self._tray.activated.connect(self._on_tray_activated)
        self._tray.show()

    def _connect_signals(self):
        self._signals.enrollment_progress.connect(self._on_progress)
        self._signals.enrollment_completed.connect(self._on_enrollment_done)
        self._wizard._progress_bar.valueChanged.connect(self._sync_top_progress)

    def _sync_top_progress(self, value: int):
        self._top_progress.setValue(value)
        days_done = round(value / 100 * ENROLLMENT_DAYS)
        self._header_badge.setText(f"Day {days_done} / {ENROLLMENT_DAYS}")

    def _on_progress(self, progress: float):
        pct = int(progress * 100)
        self._top_progress.setValue(pct)
        days_done = round(progress * ENROLLMENT_DAYS)
        self._header_badge.setText(f"Day {days_done} / {ENROLLMENT_DAYS}")
        self._status_lbl.setText(
            f"⚡  {pct}% complete — {ENROLLMENT_DAYS - days_done} day(s) remaining"
        )

    def _on_enrollment_done(self):
        """Enrollment finished — hide overlay, signal main window to show."""
        logger.info("Enrollment complete — switching to main UI")
        if self._tray:
            self._tray.showMessage(
                APP_NAME,
                "✅ Enrollment complete! GuardianAI is now active.",
                QSystemTrayIcon.Information,
                4000,
            )
        self.hide()
        self._signals.dashboard_update.emit({"enrollment_done": True})

    def _on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self._show_and_raise()

    def _show_and_raise(self):
        self.show()
        self.raise_()
        self.activateWindow()

    def _quit(self):
        if self._app_core:
            self._app_core.shutdown()
        QApplication.quit()

    def closeEvent(self, event):
        """Minimize to tray instead of closing."""
        if self._tray and self._tray.isVisible():
            self.hide()
            self._tray.showMessage(
                APP_NAME,
                "Enrollment continues in the background. Click here to reopen.",
                QSystemTrayIcon.Information,
                3000,
            )
            event.ignore()
        else:
            event.accept()

"""Enrollment Wizard — guided 7-day behavioral enrollment in the new theme.

Preserves the proven timed-typing workflow; only the visual layer is
moved onto the GuardianAI design-system tokens.
"""

from __future__ import annotations

import re
import logging
from typing import Optional

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QPushButton, QProgressBar, QStackedWidget,
    QGraphicsDropShadowEffect, QScrollArea,
)

from src.utils.signals import get_signals
from src.utils.constants import ENROLLMENT_DAYS
from src.ui.typing_test import TypingTestWidget
from src.ui.theme import (
    with_alpha,
    PRIMARY, AI, SUCCESS, WARNING, CRITICAL, MUTED, TEXT_PRI, TEXT_SEC,
    TEXT_DIM, BORDER, BORDER_STRONG, severity_color,
)

logger = logging.getLogger(__name__)

ASSIGNMENT_DATA = {
    1: {
        "title": "✍️ Natural Typing",
        "subtitle": "Day 1 — Baseline Assessment",
        "description": "Write naturally about any topic. We'll learn your natural typing rhythm, "
                       "keystroke patterns, and baseline behavior. Just type as you normally would.",
        "icon": "⌨️", "color": SUCCESS, "duration": "25 min",
        "objectives": ["Establish typing baseline", "Capture keystroke dynamics", "Measure natural WPM"],
        "has_typing_test": True, "typing_passages": "mixed",
    },
    2: {
        "title": "📝 Copy Typing",
        "subtitle": "Day 2 — Accuracy Assessment",
        "description": "Type the text passages shown on screen as accurately as possible. "
                       "This measures your typing precision and error correction patterns.",
        "icon": "📄", "color": PRIMARY, "duration": "20 min",
        "objectives": ["Measure typing accuracy", "Analyze error patterns", "Track correction behavior"],
        "has_typing_test": True, "typing_passages": "medium",
    },
    3: {
        "title": "🖱️ Mouse Interaction",
        "subtitle": "Day 3 — Navigation Assessment",
        "description": "Complete interactive clicking and dragging tasks. "
                       "We'll learn your mouse movement characteristics and interaction patterns.",
        "icon": "🖱️", "color": WARNING, "duration": "20 min",
        "objectives": ["Capture mouse movement patterns", "Analyze click precision", "Measure reaction times"],
        "has_typing_test": False, "typing_passages": None,
    },
    4: {
        "title": "📜 Scrolling & Navigation",
        "subtitle": "Day 4 — Browsing Assessment",
        "description": "Review and navigate through content naturally. "
                       "This captures your scrolling speed, reading patterns, and navigation habits.",
        "icon": "📜", "color": AI, "duration": "20 min",
        "objectives": ["Capture scroll patterns", "Analyze reading speed", "Measure navigation flow"],
        "has_typing_test": True, "typing_passages": "easy",
    },
    5: {
        "title": "💼 Mixed Productivity",
        "subtitle": "Day 5 — Comprehensive Assessment",
        "description": "Perform various desktop tasks combining typing, navigation, and interaction. "
                       "We'll capture integrated behavioral patterns across different activities.",
        "icon": "💼", "color": PRIMARY, "duration": "35 min",
        "objectives": ["Combine all behavioral modes", "Identify cross-pattern correlations", "Build comprehensive profile"],
        "has_typing_test": True, "typing_passages": "hard",
    },
    6: {
        "title": "🌿 Free Usage",
        "subtitle": "Day 6 — Natural Observation",
        "description": "Use your computer normally for an extended period. "
                       "No structured tasks — just your natural workflow.",
        "icon": "🌿", "color": SUCCESS, "duration": "60+ min",
        "objectives": ["Observe natural behavior", "Validate against structured data", "Ensure ecological validity"],
        "has_typing_test": False, "typing_passages": None,
    },
    7: {
        "title": "🎯 Final Validation",
        "subtitle": "Day 7 — Model Training",
        "description": "All collected behavioral data will be used to train your personalized "
                       "authentication model. No action needed from you.",
        "icon": "🎯", "color": CRITICAL, "duration": "Auto",
        "objectives": ["Train initial auth model", "Validate model accuracy", "Deploy to production"],
        "has_typing_test": False, "typing_passages": None,
    },
}


def parse_duration_minutes(duration_str: str) -> int:
    """Parse a duration string like '25 min' or '60+ min' into minutes."""
    match = re.search(r'(\d+)', duration_str)
    if match:
        return max(1, int(match.group(1)))
    return 5  # fallback


class GlassCard(QFrame):
    """Design-system glass card used across the wizard."""

    def __init__(self, title: str = "", content: str = "", icon: str = "",
                 color: str = SUCCESS):
        super().__init__()
        self.setObjectName("glassCard")
        self.setStyleSheet(f"""
            QFrame#glassCard {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #EB181F29, stop:1 #F50E1219);
                border: 1px solid {with_alpha(color, '44')};
                border-top: 1px solid #14FFFFFF;
                border-radius: 16px;
                padding: 20px;
            }}
        """)
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(30)
        shadow.setColor(QColor(with_alpha(color, '30')))
        shadow.setOffset(0, 4)
        self.setGraphicsEffect(shadow)

        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        layout.setContentsMargins(20, 20, 20, 20)

        if icon:
            il = QLabel(icon)
            il.setStyleSheet("font-size: 32px; background: transparent;")
            layout.addWidget(il)
        if title:
            tl = QLabel(title)
            tl.setStyleSheet(f"font-size: 16px; font-weight: bold; color: {color}; background: transparent;")
            tl.setWordWrap(True)
            layout.addWidget(tl)
        if content:
            cl = QLabel(content)
            cl.setStyleSheet(f"font-size: 13px; color: {TEXT_SEC}; background: transparent;")
            cl.setWordWrap(True)
            layout.addWidget(cl)


class DayCard(QFrame):
    """A clickable day card for the enrollment timeline."""

    clicked = Signal(int)

    def __init__(self, day: int, title: str, color: str, icon: str,
                 completed: bool = False, active: bool = False):
        super().__init__()
        self._day = day
        self._completed = completed
        self._active = active
        self._color = color
        self.setObjectName("dayCard")
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedSize(140, 155)
        self._update_style()

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(6)
        layout.setContentsMargins(0, 0, 0, 0)

        badge = QFrame()
        badge.setObjectName("dayBadge")
        badge.setFixedSize(36, 36)
        badge.setStyleSheet(f"""
            QFrame#dayBadge {{
                background: {color if completed or active else '#2A3440'};
                border: none;
                border-radius: 18px;
                padding: 0px;
            }}
        """)
        bl = QVBoxLayout(badge)
        bl.setAlignment(Qt.AlignCenter)
        bl.setContentsMargins(0, 0, 0, 0)
        nl = QLabel("✓" if completed else str(day))
        nl.setStyleSheet("font-size: 14px; font-weight: bold; color: #fff; background: transparent;")
        nl.setAlignment(Qt.AlignCenter)
        bl.addWidget(nl)
        layout.addWidget(badge, 0, Qt.AlignCenter)

        il = QLabel(icon)
        il.setAlignment(Qt.AlignCenter)
        il.setStyleSheet("font-size: 22px; background: transparent;")
        layout.addWidget(il)

        # Readable day name (text after the leading emoji), e.g. "Natural Typing"
        parts = title.split(maxsplit=1)
        label_text = parts[1] if len(parts) > 1 else title
        tl = QLabel(label_text)
        tl.setAlignment(Qt.AlignCenter)
        tl.setWordWrap(True)
        tl.setStyleSheet(f"font-size: 11px; color: {'#fff' if active else TEXT_SEC}; background: transparent;")
        layout.addWidget(tl)

    def _update_style(self):
        border = f"2px solid {self._color}" if self._active else f"1px solid {BORDER_STRONG}"
        if self._active:
            col = QColor(self._color)
            col.setAlpha(38)  # ~15% tint — visible glow over the dark surface
            bg = col.name(QColor.HexArgb)  # #AARRGGBB — valid QSS color
        else:
            bg = "#E61A212B"  # near-opaque dark glass — clearly visible
        self.setStyleSheet(f"""
            QFrame#dayCard {{
                background-color: {bg};
                border: {border};
                border-radius: 16px;
                padding: 10px;
            }}
        """)

    def mousePressEvent(self, event):
        self.clicked.emit(self._day)
        super().mousePressEvent(event)

    def set_completed(self, completed: bool):
        self._completed = completed
        self._update_style()
        self.update()

    def set_active(self, active: bool):
        self._active = active
        self._update_style()
        self.update()


class ObjectiveItem(QFrame):
    """A single objective item with check indicator."""

    def __init__(self, text: str, completed: bool = False):
        super().__init__()
        self.setStyleSheet("background: transparent;")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 4, 0, 4)
        layout.setSpacing(8)
        ind = QLabel("✓" if completed else "○")
        ind.setStyleSheet(f"font-size: 14px; font-weight: bold; color: {SUCCESS if completed else TEXT_DIM}; background: transparent;")
        layout.addWidget(ind)
        tl = QLabel(text)
        tl.setStyleSheet(f"font-size: 13px; color: {TEXT_PRI if completed else TEXT_SEC}; background: transparent;")
        tl.setWordWrap(True)
        layout.addWidget(tl, 1)


class DayPageWidget(QWidget):
    """A single day's content page with its own typing test and controls."""

    day_completed = Signal(int, dict)  # day_number, results

    def __init__(self, day: int, data: dict):
        super().__init__()
        self.day = day
        self.data = data
        self._results: Optional[dict] = None
        self._setup_ui()

    def _setup_ui(self):
        data = self.data
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(0, 0, 0, 0)

        layout.addWidget(GlassCard(
            title=data["subtitle"], content=data["description"],
            icon=data["icon"], color=data["color"],
        ))

        obj_frame = QFrame()
        obj_frame.setStyleSheet(f"background: #99151B23; border: 1px solid {BORDER_STRONG}; border-radius: 12px; padding: 16px;")
        obj_layout = QVBoxLayout(obj_frame)
        obj_layout.setContentsMargins(16, 12, 16, 12)
        obj_layout.setSpacing(4)
        obj_title = QLabel("🎯  Objectives")
        obj_title.setStyleSheet(f"font-size: 14px; font-weight: bold; color: {TEXT_SEC}; background: transparent;")
        obj_layout.addWidget(obj_title)
        for obj_text in data["objectives"]:
            obj_layout.addWidget(ObjectiveItem(obj_text))
        layout.addWidget(obj_frame)

        info_layout = QHBoxLayout()
        info_layout.setSpacing(12)

        duration_minutes = parse_duration_minutes(data["duration"])
        self._duration_seconds = duration_minutes * 60
        self._difficulty = data.get("typing_passages", "medium")

        dur_badge = QLabel(f"⏱️  {data['duration']}")
        dur_badge.setStyleSheet(f"background: {with_alpha(data['color'], '22')}; color: {data['color']}; "
                                f"padding: 6px 14px; border-radius: 8px; font-size: 12px; "
                                f"font-weight: bold; border: 1px solid {with_alpha(data['color'], '44')};")
        info_layout.addWidget(dur_badge)

        type_text = "⌨️  Timed Typing Test" if data["has_typing_test"] else "👁️  Observation"
        type_color = PRIMARY if data["has_typing_test"] else SUCCESS
        type_badge = QLabel(type_text)
        type_badge.setStyleSheet(f"background: {with_alpha(type_color, '22')}; color: {type_color}; "
                                 f"padding: 6px 14px; border-radius: 8px; font-size: 12px; "
                                 f"font-weight: bold; border: 1px solid {with_alpha(type_color, '44')};")
        info_layout.addWidget(type_badge)
        info_layout.addStretch()
        layout.addLayout(info_layout)

        if data["has_typing_test"]:
            typing_frame = QFrame()
            typing_frame.setStyleSheet(f"background: #D90B0E13; border: 1px solid {BORDER_STRONG}; border-radius: 16px; padding: 8px;")
            typing_layout = QVBoxLayout(typing_frame)
            typing_layout.setContentsMargins(16, 16, 16, 16)

            self._typing_test = TypingTestWidget()
            self._typing_test.session_completed.connect(self._on_session_done)
            typing_layout.addWidget(self._typing_test)
            layout.addWidget(typing_frame, 1)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self._start_btn = QPushButton("▶  Start Assignment")
        self._start_btn.setStyleSheet(f"""
            QPushButton {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {data['color']}, stop:1 {with_alpha(data['color'], 'CC')});
                color: #04121A; padding: 12px 32px; border-radius: 10px;
                font-size: 14px; font-weight: bold; border: none;
            }}
            QPushButton:hover {{ background: {with_alpha(data['color'], 'E6')}; }}
            QPushButton:disabled {{ background: #1A2029; color: #445060; }}
        """)
        self._start_btn.clicked.connect(self._start_session)
        btn_layout.addWidget(self._start_btn)

        self._complete_btn = QPushButton("✓  Mark Complete")
        self._complete_btn.setEnabled(False)
        self._complete_btn.setStyleSheet(f"""
            QPushButton {{
                background: {with_alpha(SUCCESS, '22')}; color: {SUCCESS};
                border: 1px solid {with_alpha(SUCCESS, '66')}; padding: 12px 32px;
                border-radius: 10px; font-size: 14px; font-weight: bold;
            }}
            QPushButton:hover {{ background: {with_alpha(SUCCESS, '33')}; border: 1px solid {SUCCESS}; }}
            QPushButton:disabled {{ background: #14181F; color: #3A4450; border: 1px solid #232B36; }}
        """)
        self._complete_btn.clicked.connect(self._complete_day)
        btn_layout.addWidget(self._complete_btn)

        if data["has_typing_test"] and hasattr(self, '_typing_test'):
            self._typing_test.set_control_buttons(self._start_btn, self._complete_btn)

        if not data["has_typing_test"]:
            self._start_btn.setVisible(False)
            self._complete_btn.setEnabled(True)
            self._complete_btn.setText("✓  Mark as Observed")

        layout.addLayout(btn_layout)
        layout.addStretch()

    def _start_session(self):
        if hasattr(self, '_typing_test'):
            self._typing_test.start_timed_session(
                duration_seconds=self._duration_seconds,
                difficulty=self._difficulty,
            )
            self._start_btn.setEnabled(False)
            self._start_btn.setText("▶  Session Running...")

    def _on_session_done(self, results: dict):
        self._results = results
        self._complete_btn.setEnabled(True)
        self._start_btn.setEnabled(False)
        self._start_btn.setText("✓  Done")

    def _complete_day(self):
        if self._results:
            self.day_completed.emit(self.day, self._results)
        else:
            self.day_completed.emit(self.day, {
                "wpm": 0, "accuracy": 0, "error_rate": 0,
                "passages_completed": 0, "total_keystrokes": 0,
                "elapsed_seconds": 0, "observation_only": True,
            })


class EnrollmentWizardWidget(QWidget):
    """Design-system enrollment wizard with timer-based typing tests."""

    def __init__(self):
        super().__init__()
        self._signals = get_signals()
        self._current_day = 1
        self._completed_days: set[int] = set()
        self._typing_results: dict[int, dict] = {}
        self._setup_ui()
        self._connect_signals()
        self._show_day(1)

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("""
            QScrollArea { background: transparent; border: none; }
            QScrollBar:vertical { background: transparent; width: 8px; }
            QScrollBar::handle:vertical { background: #2A3440; border-radius: 4px; min-height: 30px; }
        """)

        content = QWidget()
        content.setStyleSheet("background: transparent;")
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(32, 32, 32, 32)
        content_layout.setSpacing(24)

        # ── Header ──────────────────────────────────────────────────
        header_frame = QFrame()
        header_frame.setStyleSheet("background: transparent;")
        header_layout = QHBoxLayout(header_frame)
        header_layout.setContentsMargins(0, 0, 0, 0)

        header_text = QVBoxLayout()
        header_text.setSpacing(4)
        self._header_title = QLabel("📋  Behavioral Enrollment")
        self._header_title.setStyleSheet(f"font-size: 28px; font-weight: bold; color: {TEXT_PRI}; background: transparent;")
        header_text.addWidget(self._header_title)
        self._header_subtitle = QLabel("Complete 7 daily assignments to build your personalized authentication profile")
        self._header_subtitle.setStyleSheet(f"font-size: 14px; color: {TEXT_SEC}; background: transparent;")
        header_text.addWidget(self._header_subtitle)
        header_layout.addLayout(header_text)
        header_layout.addStretch()

        self._progress_badge = QLabel("0% Complete")
        self._progress_badge.setStyleSheet(f"""
            QLabel {{ background: {with_alpha(AI, '22')}; color: {AI}; padding: 6px 16px;
                     border-radius: 12px; font-size: 13px; font-weight: bold;
                     border: 1px solid {with_alpha(AI, '44')}; }}
        """)
        header_layout.addWidget(self._progress_badge)
        content_layout.addWidget(header_frame)

        # ── Progress Bar ────────────────────────────────────────────
        progress_frame = QFrame()
        progress_frame.setStyleSheet(f"background: #10141B; border-radius: 12px; padding: 16px 20px; border: 1px solid {BORDER_STRONG};")
        progress_layout = QVBoxLayout(progress_frame)
        progress_layout.setSpacing(8)
        progress_layout.setContentsMargins(20, 16, 20, 16)

        progress_header = QHBoxLayout()
        self._progress_label = QLabel("Overall Progress")
        self._progress_label.setStyleSheet(f"font-size: 13px; font-weight: bold; color: {TEXT_SEC}; background: transparent;")
        progress_header.addWidget(self._progress_label)
        progress_header.addStretch()
        self._progress_percent = QLabel("0%")
        self._progress_percent.setStyleSheet(f"font-size: 13px; font-weight: bold; color: {AI}; background: transparent;")
        progress_header.addWidget(self._progress_percent)
        progress_layout.addLayout(progress_header)

        self._progress_bar = QProgressBar()
        self._progress_bar.setRange(0, 100)
        self._progress_bar.setValue(0)
        self._progress_bar.setTextVisible(False)
        self._progress_bar.setFixedHeight(8)
        self._progress_bar.setStyleSheet("""
            QProgressBar { background: #1A2029; border: none; border-radius: 4px; }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #00D4FF, stop:0.5 #7C4DFF, stop:1 #00E676);
                border-radius: 4px;
            }
        """)
        progress_layout.addWidget(self._progress_bar)
        content_layout.addWidget(progress_frame)

        # ── Day Timeline ────────────────────────────────────────────
        timeline_frame = QFrame()
        timeline_frame.setStyleSheet("background: transparent;")
        timeline_layout = QHBoxLayout(timeline_frame)
        timeline_layout.setSpacing(8)
        timeline_layout.setContentsMargins(0, 0, 0, 0)

        self._day_cards: list[DayCard] = []
        for day in range(1, ENROLLMENT_DAYS + 1):
            data = ASSIGNMENT_DATA[day]
            card = DayCard(day, data["title"], data["color"], data["icon"],
                           completed=False, active=(day == 1))
            card.clicked.connect(self._on_day_card_clicked)
            self._day_cards.append(card)
            timeline_layout.addWidget(card)
        timeline_layout.addStretch()
        content_layout.addWidget(timeline_frame)

        # ── Day Content Stack ───────────────────────────────────────
        self._content_stack = QStackedWidget()
        self._content_stack.setStyleSheet("background: transparent;")

        self._day_pages: list[DayPageWidget] = []
        for day in range(1, ENROLLMENT_DAYS + 1):
            page = DayPageWidget(day, ASSIGNMENT_DATA[day])
            page.day_completed.connect(self._on_day_completed)
            self._day_pages.append(page)
            self._content_stack.addWidget(page)

        content_layout.addWidget(self._content_stack, 1)

        scroll.setWidget(content)
        layout.addWidget(scroll)

    def _connect_signals(self):
        self._signals.enrollment_progress.connect(self._on_progress)
        self._signals.enrollment_completed.connect(self._on_completed)

    def _on_day_card_clicked(self, day: int):
        self._show_day(day)

    def _show_day(self, day: int):
        self._current_day = day
        if 1 <= day <= ENROLLMENT_DAYS:
            self._content_stack.setCurrentIndex(day - 1)
            for i, card in enumerate(self._day_cards):
                card.set_active(i + 1 == day)

    def _on_day_completed(self, day: int, results: dict):
        self._completed_days.add(day)
        self._typing_results[day] = results
        self._day_cards[day - 1].set_completed(True)

        self._signals.assignment_completed.emit(f"day_{day}")

        progress = len(self._completed_days) / ENROLLMENT_DAYS
        self._progress_bar.setValue(int(progress * 100))
        self._progress_percent.setText(f"{int(progress * 100)}%")
        self._progress_badge.setText(f"{int(progress * 100)}% Complete")
        self._signals.enrollment_progress.emit(progress)

        logger.info(f"Day {day} completed: {results.get('wpm', 0)} WPM, "
                    f"{results.get('accuracy', 0):.1f}% accuracy, "
                    f"{results.get('passages_completed', 0)} passages")

        if len(self._completed_days) >= ENROLLMENT_DAYS:
            self._signals.enrollment_completed.emit()

    def _on_progress(self, progress: float):
        self._progress_bar.setValue(int(progress * 100))
        self._progress_percent.setText(f"{int(progress * 100)}%")
        self._progress_badge.setText(f"{int(progress * 100)}% Complete")

    def _on_completed(self):
        self._progress_bar.setValue(100)
        self._progress_percent.setText("100%")
        self._progress_badge.setText("✅ 100% Complete")
        self._progress_badge.setStyleSheet(f"""
            QLabel {{ background: {with_alpha(SUCCESS, '22')}; color: {SUCCESS}; padding: 6px 16px;
                     border-radius: 12px; font-size: 13px; font-weight: bold;
                     border: 1px solid {with_alpha(SUCCESS, '44')}; }}
        """)
        self._header_subtitle.setText("🎉 All assignments completed! Your behavioral profile is being built.")

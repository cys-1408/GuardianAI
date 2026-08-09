"""Typing Test Widget - Timer-based interactive typing test for behavioral enrollment.

Reworks the typing test into a **timed session** model:
  1. User clicks start — a countdown timer begins for the assigned duration
  2. A passage is shown; user types it with real-time character highlighting
  3. When the passage is completed, a NEW passage loads automatically
  4. Passages keep cycling until the timer reaches zero
  5. All metrics are cumulative across all passages typed
  6. When time expires, a summary of the entire session is emitted
"""

import random
import time
import logging
from datetime import datetime
from typing import Optional

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QFont, QColor
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QPushButton, QPlainTextEdit, QProgressBar,
    QSizePolicy, QGraphicsDropShadowEffect,
)

from src.ui.theme import with_alpha

logger = logging.getLogger(__name__)

# ── Typing Test Passages ──────────────────────────────────────────────

TYPING_PASSAGES = [
    "The quick brown fox jumps over the lazy dog near the bank of the river. "
    "She sells seashells by the seashore, and the shells she sells are surely seashells. "
    "A journey of a thousand miles begins with a single step toward your destination.",

    "Technology has transformed the way we communicate with each other across the globe. "
    "From the invention of the printing press to the rise of the internet, each innovation "
    "has brought us closer together. The future promises even more remarkable changes.",

    "In the realm of computer security, behavioral authentication represents a paradigm shift. "
    "Instead of relying on static passwords, we analyze unique patterns in how you interact "
    "with your device. This creates a continuous and privacy-preserving security model.",

    "Creativity is intelligence having fun in a world full of possibilities and opportunities. "
    "Every great achievement starts with a single thought and the courage to pursue it. "
    "The human mind is capable of extraordinary things when given the chance to explore.",

    "Machine learning algorithms can identify subtle patterns that humans might overlook. "
    "By analyzing vast amounts of data, these systems can make predictions and decisions "
    "with remarkable accuracy. The key is training them with diverse and representative data.",

    "The beautiful morning sun rose over the peaceful valley, casting golden rays across "
    "the green fields. Birds began to sing their cheerful songs as the world awakened to "
    "a new day full of promise and endless possibilities waiting to be discovered.",

    "Reading books opens doors to new worlds and ideas that can transform your perspective "
    "on life. Each page turned is a step toward greater understanding and wisdom that "
    "enriches your mind and spirit in ways that few other activities can match.",
]

EASY_PASSAGES = [
    "The cat sat on the mat and looked at the rat. The rat ran away from the cat very fast.",
    "I like to read books and write stories every single day of the week.",
    "The sun is bright and warm. The birds sing in the trees all day long.",
    "She went to the store to buy some milk and bread for her family dinner tonight.",
    "He loves to play games and watch movies on his computer every weekend.",
]

MEDIUM_PASSAGES = [
    "Learning to type quickly and accurately is an essential skill in the modern digital world. "
    "Practice every day to improve your speed and reduce errors over time.",

    "The human brain processes visual information in a remarkable way, recognizing patterns "
    "and faces in milliseconds. This natural ability helps us navigate the world around us.",

    "A healthy lifestyle includes regular exercise, balanced nutrition, and adequate sleep. "
    "These three pillars work together to keep both body and mind functioning at their best.",

    "The internet has revolutionized how we access information and connect with others. "
    "From social media to online learning, the digital age offers unprecedented opportunities.",
]

HARD_PASSAGES = [
    "Quantum computing leverages the principles of quantum mechanics to process information "
    "in fundamentally new ways. Unlike classical bits, quantum bits or qubits can exist in "
    "multiple states simultaneously, enabling exponentially faster computations for specific tasks.",

    "Behavioral biometrics is an interdisciplinary field combining psychology, statistics, "
    "and machine learning. By analyzing typing rhythms, mouse movements, and scrolling patterns, "
    "it creates a unique behavioral fingerprint that is extremely difficult to replicate.",

    "The Renaissance period marked a profound transformation in European culture, art, and "
    "intellectual thought. This flowering of human creativity produced masterpieces that continue "
    "to inspire and influence generations long after their creators have passed into history.",
]

ALL_PASSAGES = {
    "easy": EASY_PASSAGES,
    "medium": MEDIUM_PASSAGES + TYPING_PASSAGES[:3],
    "hard": HARD_PASSAGES + TYPING_PASSAGES[2:5],
}


class TypingStatsCard(QFrame):
    """A metric card showing a single typing statistic."""

    def __init__(self, label: str, value: str = "—", color: str = "#00E676", icon: str = ""):
        super().__init__()
        self.setFixedSize(132, 90)
        self.setStyleSheet(f"""
            QFrame {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #232B36, stop:1 #0F131A);
                border: 1px solid {with_alpha(color, '40')};
                border-radius: 12px;
                padding: 8px;
            }}
        """)
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(15)
        shadow.setColor(QColor(with_alpha(color, '30')))
        shadow.setOffset(0, 3)
        self.setGraphicsEffect(shadow)

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(2)
        layout.setContentsMargins(4, 4, 4, 4)

        if icon:
            icon_lbl = QLabel(icon)
            icon_lbl.setAlignment(Qt.AlignCenter)
            icon_lbl.setStyleSheet("font-size: 16px; background: transparent;")
            layout.addWidget(icon_lbl)

        self._value_lbl = QLabel(value)
        self._value_lbl.setAlignment(Qt.AlignCenter)
        self._value_lbl.setStyleSheet(f"font-size: 24px; font-weight: bold; color: {color}; background: transparent;")
        layout.addWidget(self._value_lbl)

        label_lbl = QLabel(label)
        label_lbl.setAlignment(Qt.AlignCenter)
        label_lbl.setStyleSheet("font-size: 10px; color: #94A3B8; background: transparent;")
        layout.addWidget(label_lbl)

    def set_value(self, value: str, color: Optional[str] = None):
        self._value_lbl.setText(value)
        if color:
            self._value_lbl.setStyleSheet(f"font-size: 24px; font-weight: bold; color: {color}; background: transparent;")


class HighlightedTextDisplay(QFrame):
    """Displays the target text with character-by-character highlighting."""

    def __init__(self):
        super().__init__()
        self.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #151B23, stop:1 #0B0E13);
                border: 1px solid #2A3440;
                border-radius: 12px;
                padding: 20px;
            }
        """)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)

        self._text_label = QLabel()
        self._text_label.setWordWrap(True)
        self._text_label.setTextFormat(Qt.RichText)
        self._text_label.setMinimumHeight(80)
        self._text_label.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        font = QFont("Consolas", 15)
        self._text_label.setFont(font)
        self._text_label.setStyleSheet("background: transparent;")
        self._text_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        layout.addWidget(self._text_label)

        self._target_text = ""
        self._typed_text = ""

    def set_target_text(self, text: str):
        self._target_text = text
        self._typed_text = ""
        self._render()

    def update_typed(self, typed: str):
        self._typed_text = typed
        self._render()

    def _render(self):
        if not self._target_text:
            self._text_label.setText("")
            return
        html_parts = []
        target = self._target_text
        typed = self._typed_text
        for i, target_char in enumerate(target):
            if i < len(typed):
                typed_char = typed[i]
                if typed_char == target_char:
                    html_parts.append(f'<span style="color: #00E676;">{self._escape(target_char)}</span>')
                else:
                    html_parts.append(f'<span style="color: #FF5252; background: #20FF5252; text-decoration: underline;">{self._escape(typed_char)}</span>')
            elif i == len(typed):
                html_parts.append(f'<span style="color: #fff; background: #807C4DFF; border-bottom: 2px solid #7C4DFF;">{self._escape(target_char)}</span>')
            else:
                html_parts.append(f'<span style="color: #5B6B7F;">{self._escape(target_char)}</span>')
        self._text_label.setText("".join(html_parts))

    @staticmethod
    def _escape(char: str) -> str:
        if char == " ":
            return "&nbsp;"
        if char == "\n":
            return "<br>"
        if char == "<":
            return "&lt;"
        if char == ">":
            return "&gt;"
        if char == "&":
            return "&amp;"
        return char


class TypingInput(QPlainTextEdit):
    """Custom text input that captures keystroke timing."""

    keystroke_signal = Signal(str, float)  # character, timestamp

    def __init__(self):
        super().__init__()
        self.setMaximumHeight(80)
        self.setPlaceholderText("Start typing here...")
        font = QFont("Consolas", 15)
        self.setFont(font)
        self.setStyleSheet("""
            QPlainTextEdit {
                background: #0B0E13;
                color: #fff;
                border: 2px solid #2A3440;
                border-radius: 12px;
                padding: 14px;
                selection-background-color: #807C4DFF;
            }
            QPlainTextEdit:focus {
                border: 2px solid #7C4DFF;
            }
            QPlainTextEdit:disabled {
                background: #0a0a10;
                color: #444;
                border: 2px solid #1a1a2e;
            }
        """)
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(20)
        shadow.setColor(QColor("#307C4DFF"))
        shadow.setOffset(0, 4)
        self.setGraphicsEffect(shadow)
        self._last_key_time = time.time()

    def keyPressEvent(self, event):
        from PySide6.QtGui import QKeyEvent
        now = time.time()
        char = event.text() if event.text() else ""
        if char:
            self.keystroke_signal.emit(char, now)
        self._last_key_time = now
        super().keyPressEvent(event)


class TypingTestWidget(QWidget):
    """Timer-based continuous typing test for behavioral enrollment.

    Features:
      - Fixed-duration countdown timer (set by caller)
      - Infinite passage cycling until time runs out
      - Real-time character highlighting (correct / error / current)
      - Cumulative metrics: WPM, Accuracy, Error Rate, Passages Completed
      - Per-passage completion tracking
      - Final results emitted when timer ends
    """

    # Emitted when the timed session ends with cumulative results
    session_completed = Signal(dict)

    # Emitted each time a passage is completed (for live progress)
    passage_completed = Signal(dict)

    def __init__(self):
        super().__init__()
        # ── Session state ────────────────────────────────────────────
        self._passage = ""
        self._typed = ""
        self._start_time: Optional[float] = None
        self._session_duration = 0       # total seconds for this session
        self._time_remaining = 0         # countdown in seconds
        self._is_active = False
        self._is_paused = False

        # ── Cumulative metrics ───────────────────────────────────────
        self._total_keystrokes = 0
        self._cumulative_correct = 0
        self._cumulative_errors = 0
        self._passages_completed = 0
        self._passage_queue: list[str] = []

        # ── Difficulty mode ──────────────────────────────────────────
        self._difficulty_pool = "medium"
        self._last_typed_len = 0  # For delta-based cumulative tracking

        self._setup_ui()
        self._setup_timers()

    # ── Public API ─────────────────────────────────────────────────────

    def start_timed_session(self, duration_seconds: int, difficulty: str = "medium") -> None:
        """Start a timed typing session.

        Args:
            duration_seconds: Total duration in seconds (e.g. 25*60 = 25 min)
            difficulty: Passage difficulty pool ("easy", "medium", "hard", "mixed")
        """
        self._session_duration = duration_seconds
        self._time_remaining = duration_seconds
        self._difficulty_pool = difficulty
        self._is_active = False
        self._is_paused = False
        self._cumulative_correct = 0
        self._cumulative_errors = 0
        self._total_keystrokes = 0
        self._passages_completed = 0
        self._start_time = None
        self._last_typed_len = 0

        # Build passage queue
        self._build_passage_queue()

        # Update UI for active state
        self._ensure_buttons()
        self._start_btn.setEnabled(False)
        self._start_btn.setText("▶  Session Active...")
        self._complete_btn.setEnabled(True)

        self._instruction_label.setText(
            f"🔴  Session active — Type continuously until the timer ends!"
        )
        self._instruction_label.setStyleSheet("""
            font-size: 12px; color: #FF5252; font-weight: bold;
            background: transparent; padding: 4px 8px;
        """)

        # Load first passage
        self._load_next_passage()
        self._typing_input.setEnabled(True)
        self._typing_input.setFocus()

        # Start timers
        self._update_timer.start(200)       # 5 Hz refresh
        self._countdown_timer.start(1000)   # 1 Hz countdown

    def stop_session(self) -> dict:
        """Forcibly stop the current session and return results."""
        if not self._is_active and self._start_time is None:
            return self._get_results()
        self._is_active = False
        self._update_timer.stop()
        self._countdown_timer.stop()
        self._typing_input.setEnabled(False)
        results = self._get_results()
        self.session_completed.emit(results)
        self._show_session_summary(results)
        return results

    def get_results(self) -> dict:
        """Get current cumulative results without stopping."""
        return self._get_results()

    # ── Private methods ────────────────────────────────────────────────

    def _build_passage_queue(self):
        """Build a shuffled queue of passages from the difficulty pool."""
        if self._difficulty_pool == "mixed":
            pool = []
            for p in ALL_PASSAGES.values():
                pool.extend(p)
        elif self._difficulty_pool in ALL_PASSAGES:
            pool = list(ALL_PASSAGES[self._difficulty_pool])
        else:
            pool = list(ALL_PASSAGES["medium"])
        random.shuffle(pool)
        self._passage_queue = pool

    def _load_next_passage(self):
        """Load the next passage from the queue (refills if empty)."""
        if not self._passage_queue:
            self._build_passage_queue()
        self._passage = self._passage_queue.pop(0)
        self._typed = ""
        self._text_display.set_target_text(self._passage)
        self._typing_input.blockSignals(True)
        self._typing_input.clear()
        self._typing_input.blockSignals(False)

    def _setup_ui(self):
        """Build the typing test interface."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        # ── Top bar: difficulty + timer ──────────────────────────────
        top_bar = QFrame()
        top_bar.setStyleSheet("background: transparent;")
        top_layout = QHBoxLayout(top_bar)
        top_layout.setContentsMargins(0, 0, 0, 0)

        top_layout.addStretch()

        self._difficulty_badge = QLabel("MEDIUM")
        self._difficulty_badge.setStyleSheet("""
            QLabel {
                background: #40FFC107;
                color: #FFC107;
                padding: 3px 10px;
                border-radius: 8px;
                font-size: 10px;
                font-weight: bold;
            }
        """)
        top_layout.addWidget(self._difficulty_badge)

        top_layout.addSpacing(16)

        # Countdown timer (prominent)
        self._countdown_label = QLabel("⏱️  00:00")
        self._countdown_label.setStyleSheet("""
            font-size: 22px; font-weight: bold; color: #00E676;
            background: transparent; font-family: 'Consolas', monospace;
        """)
        top_layout.addWidget(self._countdown_label)

        layout.addWidget(top_bar)

        # ── Stats Row ────────────────────────────────────────────────
        stats_layout = QHBoxLayout()
        stats_layout.setSpacing(8)
        self._wpm_card = TypingStatsCard("WPM", "0", "#00E676", "⚡")
        self._accuracy_card = TypingStatsCard("Accuracy", "0%", "#00D4FF", "🎯")
        self._error_card = TypingStatsCard("Error Rate", "0%", "#FF5252", "❌")
        self._keystroke_card = TypingStatsCard("Keystrokes", "0", "#FFC107", "⌨️")
        stats_layout.addWidget(self._wpm_card)
        stats_layout.addWidget(self._accuracy_card)
        stats_layout.addWidget(self._error_card)
        stats_layout.addWidget(self._keystroke_card)
        stats_layout.addStretch()
        layout.addLayout(stats_layout)

        # ── Session Progress Bar ─────────────────────────────────────
        self._session_bar = QProgressBar()
        self._session_bar.setRange(0, 100)
        self._session_bar.setValue(0)
        self._session_bar.setTextVisible(False)
        self._session_bar.setFixedHeight(6)
        self._session_bar.setStyleSheet("""
            QProgressBar {
                background: #232B36;
                border: none;
                border-radius: 3px;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #7C4DFF, stop:0.5 #FFC107, stop:1 #00E676);
                border-radius: 3px;
            }
        """)
        layout.addWidget(self._session_bar)

        # ── Typing Area ──────────────────────────────────────────────
        typing_area = QFrame()
        typing_area.setStyleSheet("""
            QFrame {
                background: #0B0E13;
                border: 1px solid #232B36;
                border-radius: 16px;
                padding: 8px;
            }
        """)
        typing_layout = QVBoxLayout(typing_area)
        typing_layout.setSpacing(8)

        self._instruction_label = QLabel("Click '▶  Start Assignment' above to begin the timed typing session")
        self._instruction_label.setStyleSheet("font-size: 12px; color: #94A3B8; background: transparent; padding: 4px 8px;")
        typing_layout.addWidget(self._instruction_label)

        self._text_display = HighlightedTextDisplay()
        typing_layout.addWidget(self._text_display)

        self._typing_input = TypingInput()
        self._typing_input.keystroke_signal.connect(self._on_keystroke)
        self._typing_input.textChanged.connect(self._on_text_changed)
        self._typing_input.setEnabled(False)
        typing_layout.addWidget(self._typing_input)

        layout.addWidget(typing_area, 1)

        # ── Bottom Controls ──────────────────────────────────────────
        controls_layout = QHBoxLayout()
        controls_layout.addStretch()

        self._reset_btn = QPushButton("🔄  Reset Session")
        self._reset_btn.setStyleSheet("""
            QPushButton {
                background: #232B36;
                color: #FFC107;
                border: 1px solid #40FFC107;
                padding: 8px 20px;
                border-radius: 8px;
                font-size: 12px;
            }
            QPushButton:hover { background: #20FFC107; border: 1px solid #FFC107; }
            QPushButton:disabled { background: #0B0E13; color: #445060; border: 1px solid #1a1a1a; }
        """)
        self._reset_btn.clicked.connect(self._on_reset)
        self._reset_btn.setEnabled(False)
        controls_layout.addWidget(self._reset_btn)

        layout.addLayout(controls_layout)

    def _setup_timers(self):
        """Setup update and countdown timers."""
        self._update_timer = QTimer(self)
        self._update_timer.timeout.connect(self._update_stats)

        self._countdown_timer = QTimer(self)
        self._countdown_timer.timeout.connect(self._on_countdown_tick)

    def _on_keystroke(self, char: str, timestamp: float):
        """Handle individual keystroke."""
        self._total_keystrokes += 1
        if not self._is_active:
            self._start_time = timestamp
            self._is_active = True

    def _on_text_changed(self):
        """Handle text changes in the typing input.

        Uses a delta-based approach to incrementally update cumulative
        metrics on each keystroke, so WPM/accuracy/error rate update
        live during typing — not just on passage completion.
        """
        if not self._is_active:
            text = self._typing_input.toPlainText()
            if text:
                self._start_time = time.time()
                self._is_active = True

        typed = self._typing_input.toPlainText()
        self._typed = typed

        # Delta-based cumulative tracking: only count NEW characters
        # since the last textChanged signal
        if len(typed) > self._last_typed_len:
            # New characters added — count them
            for i in range(self._last_typed_len, min(len(typed), len(self._passage))):
                if typed[i] == self._passage[i]:
                    self._cumulative_correct += 1
                else:
                    self._cumulative_errors += 1
            # Extra characters beyond passage length are errors
            if len(typed) > len(self._passage):
                extra = len(typed) - max(self._last_typed_len, len(self._passage))
                self._cumulative_errors += max(0, extra)
        elif len(typed) < self._last_typed_len:
            # Text was deleted (backspace) — recount from scratch
            # for correctness (simpler than un-adding)
            self._cumulative_correct = 0
            self._cumulative_errors = 0
            for i in range(min(len(typed), len(self._passage))):
                if typed[i] == self._passage[i]:
                    self._cumulative_correct += 1
                else:
                    self._cumulative_errors += 1
            if len(typed) > len(self._passage):
                self._cumulative_errors += len(typed) - len(self._passage)

        self._last_typed_len = len(typed)

        self._text_display.update_typed(typed)

        # Check if passage is complete
        if len(typed) >= len(self._passage):
            self._on_passage_complete()
            return

        self._update_stats()

    def _on_passage_complete(self):
        """Handle completion of a single passage.

        Cumulative stats are already up-to-date from _on_text_changed's
        delta tracking, so we just increment the passage counter and
        load the next passage.
        """

        self._passages_completed += 1

        # Emit passage completed signal
        self.passage_completed.emit({
            "passage": self._passages_completed,
            "cumulative_correct": self._cumulative_correct,
            "cumulative_errors": self._cumulative_errors,
            "total_keystrokes": self._total_keystrokes,
            "passage_length": len(self._passage),
        })

        # Check if timer already expired (user finished right as time ran out)
        if self._time_remaining <= 0:
            self._on_session_end()
            return

        # Load next passage
        self._load_next_passage()

        # Update instruction
        self._instruction_label.setText(
            f"✅ Great — keep typing! {self._format_time(self._time_remaining)} remaining"
        )
        self._instruction_label.setStyleSheet("""
            font-size: 12px; color: #00E676; font-weight: bold;
            background: transparent; padding: 4px 8px;
        """)

        self._update_stats()



    def _on_countdown_tick(self):
        """Handle the 1-second countdown timer tick."""
        if not self._is_active:
            return
        self._time_remaining -= 1

        # Update countdown display
        self._countdown_label.setText(f"⏱️  {self._format_time(self._time_remaining)}")

        # Color changes based on time remaining
        if self._time_remaining > 60:
            color = "#00E676"  # Green — plenty of time
        elif self._time_remaining > 15:
            color = "#FFC107"  # Orange — warning
        else:
            color = "#FF5252"  # Red — hurry!
        self._countdown_label.setStyleSheet(
            f"font-size: 22px; font-weight: bold; color: {color}; "
            f"background: transparent; font-family: 'Consolas', monospace;"
        )

        # Update progress bar (inverse — shows time used)
        if self._session_duration > 0:
            pct_used = ((self._session_duration - self._time_remaining) / self._session_duration) * 100
            self._session_bar.setValue(int(pct_used))

        # Check if time is up
        if self._time_remaining <= 0:
            self._on_session_end()

    def _on_session_end(self):
        """Handle the end of the timed session."""
        self._is_active = False
        self._update_timer.stop()
        self._countdown_timer.stop()
        self._typing_input.setEnabled(False)

        # Get final cumulative results
        results = self._get_results()

        # Update UI
        self._countdown_label.setText("⏱️  00:00")
        self._session_bar.setValue(100)

        self._instruction_label.setText("⏰  Time's up! Session complete. Review your results below.")
        self._instruction_label.setStyleSheet("""
            font-size: 14px; color: #7C4DFF; font-weight: bold;
            background: transparent; padding: 4px 8px;
        """)

        self._show_session_summary(results)
        self.session_completed.emit(results)

        # Enable complete button
        self._ensure_buttons()
        self._complete_btn.setEnabled(True)
        self._start_btn.setEnabled(False)
        self._reset_btn.setEnabled(True)

    def _show_session_summary(self, results: dict):
        """Display a summary overlay when session ends."""
        elapsed = results["elapsed_seconds"]
        minutes = int(elapsed // 60)
        seconds = int(elapsed % 60)

        summary = (
            f"⏰  Session Complete!\n\n"
            f"📊  Session Summary\n"
            f"{'─' * 30}\n"
            f"  Duration      :  {minutes}:{seconds:02d}\n"
            f"  Passages Done :  {results['passages_completed']}\n"
            f"  Keystrokes    :  {results['total_keystrokes']}\n"
            f"  Avg WPM       :  {results['wpm']}\n"
            f"  Accuracy      :  {results['accuracy']:.1f}%\n"
            f"  Error Rate    :  {results['error_rate']:.1f}%\n\n"
            f"  🟢 Correct    :  {results['correct_chars']}\n"
            f"  🔴 Errors     :  {results['error_chars']}\n"
        )

    def _update_stats(self):
        """Update all statistic cards with cumulative values."""
        elapsed = self._get_elapsed()
        minutes = max(0.001, elapsed / 60.0)
        total_chars = self._cumulative_correct + self._cumulative_errors

        # WPM: (correct chars / 5) / minutes
        wpm = int((self._cumulative_correct / 5.0) / minutes) if self._cumulative_correct > 0 else 0

        # Accuracy
        accuracy = (self._cumulative_correct / total_chars * 100) if total_chars > 0 else 100.0

        # Error rate
        error_rate = (self._cumulative_errors / total_chars * 100) if total_chars > 0 else 0.0

        # Update cards
        self._wpm_card.set_value(str(wpm))
        accuracy_color = "#00D4FF" if accuracy > 80 else "#FFC107" if accuracy > 60 else "#FF5252"
        self._accuracy_card.set_value(f"{accuracy:.1f}%", accuracy_color)
        error_color = "#00E676" if error_rate < 5 else "#FFC107" if error_rate < 15 else "#FF5252"
        self._error_card.set_value(f"{error_rate:.1f}%", error_color)
        self._keystroke_card.set_value(str(self._total_keystrokes))

    def _get_elapsed(self) -> float:
        """Get elapsed time in seconds."""
        if self._start_time is None:
            return 0.0
        return time.time() - self._start_time

    def _get_results(self) -> dict:
        """Get cumulative session results."""
        elapsed = self._get_elapsed()
        minutes = max(0.001, elapsed / 60.0)
        total_chars = self._cumulative_correct + self._cumulative_errors

        wpm = int((self._cumulative_correct / 5.0) / minutes) if self._cumulative_correct > 0 else 0
        accuracy = (self._cumulative_correct / total_chars * 100) if total_chars > 0 else 100.0
        error_rate = (self._cumulative_errors / total_chars * 100) if total_chars > 0 else 0.0

        return {
            "wpm": wpm,
            "accuracy": accuracy,
            "error_rate": error_rate,
            "total_keystrokes": self._total_keystrokes,
            "correct_chars": self._cumulative_correct,
            "error_chars": self._cumulative_errors,
            "passages_completed": self._passages_completed,
            "elapsed_seconds": elapsed,
            "session_duration": self._session_duration,
            "is_complete": not self._is_active,
            "timestamp": datetime.now().isoformat(),
        }

    def _on_reset(self):
        """Reset the typing test to idle state."""
        self._is_active = False
        self._update_timer.stop()
        self._countdown_timer.stop()
        self._typing_input.setEnabled(False)
        self._typing_input.clear()

        self._session_duration = 0
        self._time_remaining = 0
        self._cumulative_correct = 0
        self._cumulative_errors = 0
        self._total_keystrokes = 0
        self._passages_completed = 0
        self._passage_queue = []
        self._start_time = None
        self._last_typed_len = 0
        self._passage = ""
        self._typed = ""

        self._countdown_label.setText("⏱️  00:00")
        self._countdown_label.setStyleSheet("""
            font-size: 22px; font-weight: bold; color: #00E676;
            background: transparent; font-family: 'Consolas', monospace;
        """)
        self._session_bar.setValue(0)

        self._instruction_label.setText("Click '▶  Start Assignment' above to begin the timed typing session")
        self._instruction_label.setStyleSheet("font-size: 12px; color: #94A3B8; background: transparent; padding: 4px 8px;")

        self._ensure_buttons()
        self._start_btn.setEnabled(True)
        self._start_btn.setText("▶  Start Assignment")
        self._complete_btn.setEnabled(False)
        self._reset_btn.setEnabled(False)

        # Reset cards
        self._wpm_card.set_value("0")
        self._accuracy_card.set_value("0%", "#00D4FF")
        self._error_card.set_value("0%")
        self._keystroke_card.set_value("0")

        self._text_display.set_target_text("Press 'Start' to begin")

    @staticmethod
    def _format_time(seconds: int) -> str:
        """Format seconds as MM:SS."""
        m = seconds // 60
        s = seconds % 60
        return f"{m:02d}:{s:02d}"

    # ── References set by Enrollment Wizard ────────────────────────────
    # These are set externally by the enrollment wizard to bridge
    # the typing test widget with the wizard's control buttons
    def set_control_buttons(self, start_btn, complete_btn):
        self._start_btn = start_btn
        self._complete_btn = complete_btn

    def _ensure_buttons(self):
        """Create stub buttons if set_control_buttons was never called."""
        if not hasattr(self, '_start_btn'):
            self._start_btn = QPushButton()
        if not hasattr(self, '_complete_btn'):
            self._complete_btn = QPushButton()

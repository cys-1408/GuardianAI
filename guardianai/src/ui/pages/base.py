"""Base Page — shared scaffolding for every command-center screen."""

from __future__ import annotations

from typing import Any, Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QScrollArea, QSizePolicy,
)

from src.ui.theme import TEXT_PRI, TEXT_SEC, TEXT_DIM, BORDER, PRIMARY
from src.ui.widgets import GlowButton, Badge
from src.ui.state import SystemState


class BasePage(QWidget):
    """Page with header, scrollable body, and refresh hook.

    Subclasses build content in `_build()` and optionally override
    `refresh()` (called on navigation + every N seconds by the shell).
    """

    TITLE = "Page"
    ICON = "🛰"
    ACCENT = PRIMARY
    SUBTITLE = ""

    def __init__(self, state: SystemState) -> None:
        super().__init__()
        self._state = state
        self._signals = None

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Header ────────────────────────────────────────────────
        header = QFrame()
        header.setStyleSheet(
            f"QFrame {{ background: #99080A0E; border-bottom: 1px solid {BORDER}; }}"
        )
        header.setFixedHeight(64)
        hl = QHBoxLayout(header)
        hl.setContentsMargins(28, 0, 28, 0)
        hl.setSpacing(12)

        ic = QLabel(self.ICON)
        ic.setStyleSheet(f"font-size: 20px; background: transparent;")
        hl.addWidget(ic)

        col = QVBoxLayout()
        col.setSpacing(0)
        title = QLabel(self.TITLE)
        title.setStyleSheet(
            f"font-size: 17px; font-weight: 700; color: {TEXT_PRI}; background: transparent;"
        )
        col.addWidget(title)
        if self.SUBTITLE:
            sub = QLabel(self.SUBTITLE)
            sub.setStyleSheet(f"font-size: 11px; color: {TEXT_SEC}; background: transparent;")
            col.addWidget(sub)
        hl.addLayout(col)
        hl.addStretch()

        self._header_right = QHBoxLayout()
        hl.addLayout(self._header_right)
        root.addWidget(header)

        # ── Scrollable body ───────────────────────────────────────
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")

        self._body = QWidget()
        self._body.setStyleSheet("background: transparent;")
        self._body_layout = QVBoxLayout(self._body)
        self._body_layout.setContentsMargins(28, 24, 28, 24)
        self._body_layout.setSpacing(16)
        self._body_layout.addStretch()

        scroll.setWidget(self._body)
        root.addWidget(scroll, 1)

        self._build()

    # ── helpers for subclasses ────────────────────────────────────
    def add_widget(self, w: QWidget, stretch: int = 0) -> None:
        """Insert a widget before the trailing stretch."""
        self._body_layout.insertWidget(self._body_layout.count() - 1, w, stretch)

    def add_header_badge(self, text: str, severity: str = "info") -> Badge:
        badge = Badge(text, severity)
        self._header_right.addWidget(badge)
        return badge

    def add_header_action(self, text: str, handler) -> None:
        btn = GlowButton(text, kind="ghost")
        btn.clicked.connect(handler)
        self._header_right.addWidget(btn)

    def _build(self) -> None:
        """Subclasses build their UI here."""

    def refresh(self) -> None:
        """Called periodically and on navigation — re-reads real state."""

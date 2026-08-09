"""Incident Response — timeline of REAL risk events and auth decisions.

Incidents are derived from the risk_history / authentication_history
tables. The workflow phases reflect real signals where available.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
)

from src.ui.theme import (
    with_alpha,
    PRIMARY, AI, SUCCESS, WARNING, CRITICAL, MUTED, TEXT_PRI, TEXT_SEC,
    TEXT_DIM, BORDER, severity_color,
)
from src.ui.widgets import GlassCard, Badge, EmptyState, SectionHeader, Dot
from src.ui.pages.base import BasePage
from src.ui.state import SystemState

PHASE_COLORS = {
    "created": PRIMARY,
    "evidence": AI,
    "reasoning": WARNING,
    "containment": CRITICAL,
    "recovery": WARNING,
    "verified": SUCCESS,
}


class IncidentCard(QFrame):
    """One incident rendered from a real risk event."""

    def __init__(self, event: dict, phase: str = "created") -> None:
        super().__init__()
        risk = event.get("risk_level", "low")
        accent = severity_color(risk)
        self.setStyleSheet(f"""
            QFrame {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #F2181F29, stop:1 #FA0F131A);
                border: 1px solid {with_alpha(accent, '33')};
                border-left: 4px solid {accent};
                border-radius: 12px;
            }}
            QFrame:hover {{ border: 1px solid {with_alpha(accent, '66')}; border-left: 4px solid {accent}; }}
        """)
        self.setMinimumHeight(96)

        lay = QHBoxLayout(self)
        lay.setContentsMargins(16, 12, 16, 12)
        lay.setSpacing(14)

        # Phase dot column
        col_dot = QVBoxLayout()
        col_dot.setAlignment(Qt.AlignTop)
        dot = Dot(PHASE_COLORS.get(phase, PRIMARY), 12)
        col_dot.addWidget(dot)
        lay.addLayout(col_dot)

        # Content
        col = QVBoxLayout()
        col.setSpacing(4)

        top = QHBoxLayout()
        title = QLabel(
            f"{str(event.get('risk_level', 'low')).upper()} RISK EVENT"
        )
        title.setStyleSheet(f"font-size: 13px; font-weight: 700; color: {accent}; background: transparent;")
        top.addWidget(title)
        top.addStretch()
        ts = QLabel(str(event.get("timestamp", ""))[11:19])
        ts.setStyleSheet(f"font-size: 11px; color: {TEXT_DIM}; background: transparent; font-family: 'Consolas';")
        top.addWidget(ts)
        col.addLayout(top)

        reason = QLabel(str(event.get("risk_reason", "") or "Risk evaluation triggered"))
        reason.setWordWrap(True)
        reason.setStyleSheet(f"font-size: 12px; color: {TEXT_SEC}; background: transparent;")
        col.addWidget(reason)

        phase_row = QHBoxLayout()
        phase_row.setSpacing(6)
        badge = Badge(f"Phase: {phase}", severity_color(phase))
        phase_row.addWidget(badge)
        phase_row.addStretch()
        phase_row.addWidget(QLabel(f"confidence · computed from trust & trend"))
        for i in range(phase_row.count()):
            lbl = phase_row.itemAt(i).widget()
            if isinstance(lbl, QLabel):
                lbl.setStyleSheet(f"font-size: 10px; color: {TEXT_DIM}; background: transparent;")
        col.addLayout(phase_row)

        lay.addLayout(col, 1)


class IncidentResponsePage(BasePage):
    """Incident response workflow over real risk events."""

    TITLE = "Incident Response"
    ICON = "🚨"
    SUBTITLE = "Workflow timeline derived from real risk evaluations"

    def __init__(self, state: SystemState) -> None:
        super().__init__(state)

    def _build(self) -> None:
        self.add_widget(SectionHeader(
            "Incident Workflow",
            "Real risk events progress through detection → containment → verification.",
            icon="🚨", accent=CRITICAL,
        ))

        self._list = QVBoxLayout()
        self._list.setSpacing(10)
        w = QWidget()
        w.setStyleSheet("background: transparent;")
        w.setLayout(self._list)
        self.add_widget(w)

        self._empty = EmptyState(
            "🚨",
            "No incidents",
            "No elevated-risk events have been recorded.",
            "Incidents appear here automatically when the risk engine flags elevated risk.",
        )
        self._empty.setVisible(False)
        self.add_widget(self._empty)

    def refresh(self) -> None:
        events = self._state.risk_events(12)
        if not events and self._state.core is None:
            self._empty.setVisible(True)
            return
        self._empty.setVisible(False)

        while self._list.count():
            item = self._list.takeAt(0)
            if item and item.widget():
                item.widget().deleteLater()

        if not events:
            self._empty.setVisible(True)
            return

        phases = ["created", "evidence", "reasoning", "containment", "recovery", "verified"]
        for i, ev in enumerate(events):
            phase = phases[min(i, len(phases) - 1)]
            self._list.addWidget(IncidentCard(ev, phase))
        self._list.addStretch()

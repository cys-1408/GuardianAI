"""AI Agent Center — every agent reflects a REAL GuardianAI subsystem.

Status, confidence, task, decision, and recent actions are all derived
from the live application state — nothing is simulated.
"""

from __future__ import annotations

from datetime import datetime

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QGridLayout,
)

from src.ui.theme import (
    with_alpha,
    PRIMARY, AI, SUCCESS, WARNING, CRITICAL, MUTED, TEXT_PRI, TEXT_SEC,
    TEXT_DIM, BORDER, severity_color,
)
from src.ui.widgets import GlassCard, Badge, Dot, EmptyState, SectionHeader
from src.ui.pages.base import BasePage
from src.ui.state import SystemState


class AgentCard(QFrame):
    """Card for one autonomous agent (real subsystem)."""

    def __init__(self, agent: dict) -> None:
        super().__init__()
        self._agent = agent
        running = agent["status"] == "running"
        accent = severity_color(agent["status"])
        self.setStyleSheet(f"""
            QFrame {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #F2181F29, stop:1 #FA0F131A);
                border: 1px solid {with_alpha(accent, '33')};
                border-left: 3px solid {accent};
                border-radius: 12px;
            }}
            QFrame:hover {{ border: 1px solid {with_alpha(accent, '66')}; border-left: 3px solid {accent}; }}
        """)
        self.setMinimumHeight(170)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(16, 14, 16, 14)
        lay.setSpacing(6)

        top = QHBoxLayout()
        top.setSpacing(10)
        ic = QLabel(agent["icon"])
        ic.setStyleSheet(f"font-size: 22px; background: transparent;")
        top.addWidget(ic)

        col = QVBoxLayout()
        col.setSpacing(0)
        name = QLabel(agent["name"])
        name.setStyleSheet(f"font-size: 14px; font-weight: 700; color: {TEXT_PRI}; background: transparent;")
        col.addWidget(name)
        desc = QLabel(agent["description"])
        desc.setWordWrap(True)
        desc.setStyleSheet(f"font-size: 11px; color: {TEXT_DIM}; background: transparent;")
        col.addWidget(desc)
        top.addLayout(col, 1)

        badge = Badge(agent["status"].upper(), agent["status"])
        top.addWidget(badge, 0, Qt.AlignTop)
        lay.addLayout(top)

        # Task + decision
        task = QLabel(f"◈  {agent['task']}")
        task.setWordWrap(True)
        task.setStyleSheet(f"font-size: 12px; color: {TEXT_SEC}; background: transparent;")
        lay.addWidget(task)

        dec = QLabel(f"⚖  {agent['decision']}")
        dec.setWordWrap(True)
        dec.setStyleSheet(f"font-size: 11px; color: {accent}; background: transparent;")
        lay.addWidget(dec)

        # Footer: confidence + health + runtime
        foot = QHBoxLayout()
        foot.setSpacing(8)
        conf = agent["confidence"]
        conf_lbl = QLabel(f"Confidence {conf * 100:.0f}%")
        conf_lbl.setStyleSheet(
            f"font-size: 11px; font-weight: 700; color: {severity_color('success' if conf > 0.6 else 'warning' if conf > 0.3 else 'critical')}; background: transparent;"
        )
        foot.addWidget(conf_lbl)
        foot.addStretch()
        health = agent["health"]
        h_lbl = QLabel(f"Health {health}%")
        h_lbl.setStyleSheet(f"font-size: 11px; color: {TEXT_DIM}; background: transparent;")
        foot.addWidget(h_lbl)
        rt = QLabel(agent["runtime"])
        rt.setStyleSheet(f"font-size: 11px; color: {TEXT_DIM}; background: transparent;")
        foot.addWidget(rt)
        lay.addLayout(foot)


class AIAgentsPage(BasePage):
    """Autonomous agent center built from the real subsystem map."""

    TITLE = "AI Agent Center"
    ICON = "🤖"
    SUBTITLE = "Autonomous subsystems actively defending this endpoint"

    def __init__(self, state: SystemState) -> None:
        super().__init__(state)

    def _build(self) -> None:
        self.add_widget(SectionHeader(
            "Active Autonomous Agents",
            "Each agent maps to a real GuardianAI subsystem — status is live.",
            icon="🤖", accent=AI,
        ))

        self._grid = QGridLayout()
        self._grid.setSpacing(14)
        self._grid.setColumnStretch(0, 1)
        self._grid.setColumnStretch(1, 1)
        self._grid.setColumnStretch(2, 1)
        w = QWidget()
        w.setStyleSheet("background: transparent;")
        w.setLayout(self._grid)
        self.add_widget(w)

        self._empty = EmptyState(
            "🤖",
            "No agent data",
            "The application core is not connected in this context.",
            "Launch GuardianAI to see the live autonomous agent stack.",
        )
        self._empty.setVisible(False)
        self.add_widget(self._empty)

    def refresh(self) -> None:
        agents = self._state.agents()
        if not agents:
            self._empty.setVisible(self._state.core is None)
            return
        self._empty.setVisible(False)

        # Rebuild grid (only on change)
        while self._grid.count():
            item = self._grid.takeAt(0)
            if item and item.widget():
                item.widget().deleteLater()

        for i, agent in enumerate(agents):
            row, col = divmod(i, 3)
            self._grid.addWidget(AgentCard(agent), row, col)

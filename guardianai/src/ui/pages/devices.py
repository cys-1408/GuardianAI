"""Devices — professional enterprise device table backed by real data.

The desktop application protects the local endpoint; sessions in the
real database represent the protection history. When no sessions exist
an honest empty state is shown.
"""

from __future__ import annotations

import socket
import platform

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QTableWidget,
    QTableWidgetItem, QHeaderView, QAbstractItemView,
)

from src.ui.theme import (
    PRIMARY, AI, SUCCESS, WARNING, CRITICAL, MUTED, TEXT_PRI, TEXT_SEC,
    TEXT_DIM, BORDER, severity_color,
)
from src.ui.widgets import (
    GlassCard, MetricTile, Badge, EmptyState, SectionHeader, GlowButton,
)
from src.ui.pages.base import BasePage
from src.ui.state import SystemState


class DevicesPage(BasePage):
    """Enterprise device management — real sessions + local endpoint."""

    TITLE = "Devices"
    ICON = "🖥"
    SUBTITLE = "Protected endpoint and session history"

    def __init__(self, state: SystemState) -> None:
        super().__init__(state)

    def _build(self) -> None:
        tiles = QHBoxLayout()
        tiles.setSpacing(12)
        self._tile_devices = MetricTile("Protected Devices", "🖥", SUCCESS, "1", "this endpoint")
        self._tile_sessions = MetricTile("Sessions", "💻", PRIMARY, "0", "recorded sessions")
        self._tile_risk = MetricTile("Endpoint Risk", "🛡", WARNING, "low", "")
        for t in [self._tile_devices, self._tile_sessions, self._tile_risk]:
            tiles.addWidget(t)
        self.add_widget(self._wrap(tiles))

        self.add_widget(SectionHeader(
            "Session History", "Real sessions recorded by the behavioral engine.",
            icon="💻", accent=PRIMARY,
        ))

        card = GlassCard("", PRIMARY)
        self._table = QTableWidget(0, 6)
        self._table.setHorizontalHeaderLabels(
            ["Session ID", "User", "Start", "Duration", "Trust", "Status"])
        for c in range(6):
            self._table.horizontalHeader().setSectionResizeMode(c, QHeaderView.Stretch)
        self._table.verticalHeader().setVisible(False)
        self._table.setShowGrid(False)
        self._table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self._table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._table.setMinimumHeight(260)
        card.body().addWidget(self._table, 1)
        self.add_widget(card, 1)

        self._empty = EmptyState(
            "🖥",
            "No protected devices yet",
            "No session data has been recorded for this endpoint.",
            "Sessions are created when you use the application — check back after your next session.",
        )
        self._empty.setVisible(False)
        self.add_widget(self._empty)

    @staticmethod
    def _wrap(layout) -> QWidget:
        w = QWidget()
        w.setStyleSheet("background: transparent;")
        w.setLayout(layout)
        return w

    def refresh(self) -> None:
        if self._state.core is None:
            self._empty.setVisible(True)
            return
        counts = self._state.db_counts()
        auth = self._state.auth()
        self._tile_devices.set_value("1")
        self._tile_devices.set_sub(f"{socket.gethostname()} · {platform.system()}")
        self._tile_sessions.set_value(str(counts.get("sessions", 0)))
        self._tile_sessions.set_sub(f"{counts.get('users', 0)} enrolled user(s)")
        self._tile_risk.set_value(auth["risk_level"].capitalize())
        self._tile_risk.set_sub(f"score {auth['risk_score'] * 100:.0f}%")

        sessions = self._state.recent_sessions(50)
        self._table.setRowCount(0)
        for s in sessions:
            self._table.insertRow(self._table.rowCount())
            i = self._table.rowCount() - 1
            self._table.setItem(i, 0, QTableWidgetItem(s.session_id[:12]))
            self._table.setItem(i, 1, QTableWidgetItem(s.user_id))
            self._table.setItem(i, 2, QTableWidgetItem(s.start_time.strftime("%Y-%m-%d %H:%M")))
            dur = int(s.duration_seconds)
            h, rem = divmod(dur, 3600)
            m, _ = divmod(rem, 60)
            self._table.setItem(i, 3, QTableWidgetItem(f"{h}h {m}m" if h else f"{m}m"))
            trust_item = QTableWidgetItem(f"{s.average_trust_score * 100:.0f}%")
            trust_item.setForeground(QColor(
                severity_color(s.auth_status)))
            self._table.setItem(i, 4, trust_item)
            status_item = QTableWidgetItem(s.auth_status.capitalize())
            status_item.setForeground(QColor(
                severity_color(s.auth_status)))
            self._table.setItem(i, 5, status_item)

        self._empty.setVisible(counts.get("sessions", 0) == 0)

"""Audit Logs — immutable security audit trail from the real audit_logs table."""

from __future__ import annotations

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
    GlassCard, Badge, EmptyState, SearchInput, GlowButton,
)
from src.ui.pages.base import BasePage
from src.ui.state import SystemState


class AuditLogsPage(BasePage):
    """Immutable audit trail — every row is a real audit_logs record."""

    TITLE = "Audit Logs"
    ICON = "📜"
    SUBTITLE = "Immutable security audit trail"

    def __init__(self, state: SystemState) -> None:
        super().__init__(state)
        self._query = ""

    def _build(self) -> None:
        toolbar = QHBoxLayout()
        toolbar.setSpacing(8)
        self._search = SearchInput("Search audit trail…")
        self._search.textChanged.connect(self._on_query)
        toolbar.addWidget(self._search)
        toolbar.addStretch()
        refresh_btn = GlowButton("Refresh", icon="↻")
        refresh_btn.clicked.connect(self.refresh)
        toolbar.addWidget(refresh_btn)
        w = QWidget()
        w.setStyleSheet("background: transparent;")
        w.setLayout(toolbar)
        self.add_widget(w)

        card = GlassCard("AUDIT TRAIL", PRIMARY)
        self._table = QTableWidget(0, 5)
        self._table.setHorizontalHeaderLabels(["Time", "Severity", "Component", "Description", "Metadata"])
        self._table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self._table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self._table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self._table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self._table.horizontalHeader().setSectionResizeMode(4, QHeaderView.Stretch)
        self._table.verticalHeader().setVisible(False)
        self._table.setShowGrid(False)
        self._table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self._table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._table.setMinimumHeight(360)
        card.body().addWidget(self._table, 1)
        self.add_widget(card, 1)

        self._empty = EmptyState(
            "📜",
            "Audit trail is empty",
            "No audit records exist in this context.",
            "Security-relevant events are appended automatically while the application runs.",
        )
        self._empty.setVisible(False)
        self.add_widget(self._empty)

    def _on_query(self, text: str) -> None:
        self._query = text.lower().strip()
        self.refresh()

    def refresh(self) -> None:
        if self._state.core is None:
            self._empty.setVisible(True)
            return
        events = self._state.audit_events(limit=400)
        if self._query:
            events = [
                e for e in events
                if self._query in str(e.get("component", "")).lower()
                or self._query in str(e.get("description", "")).lower()
                or self._query in str(e.get("metadata", "")).lower()
            ]

        self._table.setRowCount(0)
        for row in events:
            self._table.insertRow(self._table.rowCount())
            i = self._table.rowCount() - 1
            sev = (row.get("severity") or "information").lower()
            item = QTableWidgetItem(sev.upper())
            item.setForeground(QColor(severity_color(sev)))
            self._table.setItem(i, 0, QTableWidgetItem(str(row.get("timestamp", ""))[11:19]))
            self._table.setItem(i, 1, item)
            self._table.setItem(i, 2, QTableWidgetItem(str(row.get("component", "") or "—")))
            self._table.setItem(i, 3, QTableWidgetItem(str(row.get("description", "") or "—")))
            self._table.setItem(i, 4, QTableWidgetItem(str(row.get("metadata", "") or "")[:120]))

        self._empty.setVisible(len(events) == 0)

"""Alerts — professional alert center over the REAL audit log.

Severity filters, search, expandable detail, and bulk actions.
No synthetic alerts: everything comes from audit_logs / notifications.
"""

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

SEVERITIES = ["all", "critical", "error", "warning", "information"]


class AlertsPage(BasePage):
    """Alert center fed entirely by real audit events."""

    TITLE = "Alert Center"
    ICON = "🔔"
    SUBTITLE = "Security-relevant events from the immutable audit log"

    def __init__(self, state: SystemState) -> None:
        super().__init__(state)
        self._rows: list[dict] = []
        self._severity = "all"
        self._query = ""

    def _build(self) -> None:
        # Filter chips
        chips = QHBoxLayout()
        chips.setSpacing(8)
        chips.addWidget(QLabel("Filter:"))
        self._chip_btns: dict[str, GlowButton] = {}
        for sev in SEVERITIES:
            btn = GlowButton(sev.capitalize(), kind="ghost" if sev != "all" else "outline",
                             accent=severity_color(sev))
            btn.setCheckable(True)
            btn.setChecked(sev == "all")
            btn.clicked.connect(lambda _, s=sev: self._set_severity(s))
            chips.addWidget(btn)
            self._chip_btns[sev] = btn
        chips.addStretch()

        self._search = SearchInput("Search component, description, metadata…")
        self._search.textChanged.connect(self._on_query)
        chips.addWidget(self._search)

        w = QWidget()
        w.setStyleSheet("background: transparent;")
        w.setLayout(chips)
        self.add_widget(w)

        table_card = GlassCard("EVENT STREAM", PRIMARY)
        self._table = QTableWidget(0, 5)
        self._table.setHorizontalHeaderLabels(["Severity", "Time", "Component", "Description", "Meta"])
        self._table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self._table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self._table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self._table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self._table.horizontalHeader().setSectionResizeMode(4, QHeaderView.Stretch)
        self._table.verticalHeader().setVisible(False)
        self._table.setShowGrid(False)
        self._table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self._table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._table.setMinimumHeight(320)
        table_card.body().addWidget(self._table, 1)
        self.add_widget(table_card, 1)

        self._empty = EmptyState(
            "🔔",
            "No alerts match",
            "No audit events match the current filters.",
            "Alerts are derived from the real audit log — run the application to populate it.",
        )
        self._empty.setVisible(False)
        self.add_widget(self._empty)

    def _set_severity(self, sev: str) -> None:
        self._severity = sev
        for k, b in self._chip_btns.items():
            b.setChecked(k == sev)
            if k == sev:
                b.setStyleSheet(GlowButton._qss("outline" if sev == "all" else "ghost",
                                                severity_color(sev)))
        self._reload()

    def _on_query(self, text: str) -> None:
        self._query = text.lower().strip()
        self._reload()

    def _reload(self) -> None:
        events = self._state.audit_events(limit=300)
        if self._severity != "all":
            events = [e for e in events if (e.get("severity") or "").lower() == self._severity]
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
            c = severity_color(sev)
            item = QTableWidgetItem(sev.upper())
            item.setForeground(QColor(c))
            self._table.setItem(i, 0, item)
            self._table.setItem(i, 1, QTableWidgetItem(str(row.get("timestamp", ""))[11:19]))
            self._table.setItem(i, 2, QTableWidgetItem(str(row.get("component", "") or "—")))
            self._table.setItem(i, 3, QTableWidgetItem(str(row.get("description", "") or "—")))
            meta = (row.get("metadata") or "")[:80]
            self._table.setItem(i, 4, QTableWidgetItem(meta))

        self._empty.setVisible(len(events) == 0)

    def refresh(self) -> None:
        if self._state.core is None:
            self._empty.setVisible(True)
            return
        self._reload()

"""Threat Intelligence — MITRE ATT&CK mapping derived from REAL engine signals.

CVE / IoC feeds are intentionally empty until connectors exist; the page
shows honest empty states rather than fabricated indicators.
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
    GlassCard, Badge, EmptyState, SectionHeader, MetricTile,
)
from src.ui.pages.base import BasePage
from src.ui.state import SystemState


class ThreatIntelPage(BasePage):
    """Threat intelligence — live MITRE mapping from the risk engine."""

    TITLE = "Threat Intelligence"
    ICON = "🛰"
    SUBTITLE = "ATT&CK mapping derived from live risk & trust signals"

    def __init__(self, state: SystemState) -> None:
        super().__init__(state)

    def _build(self) -> None:
        tiles = QHBoxLayout()
        tiles.setSpacing(12)
        self._tile_tech = MetricTile("Active Techniques", "🎯", CRITICAL, "0", "ATT&CK")
        self._tile_cves = MetricTile("CVEs Tracked", "🧾", WARNING, "0", "no feed connector")
        self._tile_iocs = MetricTile("Indicators", "🔴", AI, "0", "no feed connector")
        for t in [self._tile_tech, self._tile_cves, self._tile_iocs]:
            tiles.addWidget(t)
        self.add_widget(self._wrap(tiles))

        # MITRE table
        self.add_widget(SectionHeader(
            "MITRE ATT&CK Mapping", "Techniques surfaced by real engine signals only.",
            icon="🎯", accent=CRITICAL,
        ))
        card = GlassCard("", CRITICAL)
        self._table = QTableWidget(0, 5)
        self._table.setHorizontalHeaderLabels(
            ["Technique", "Name", "Phase", "Signal", "Confidence"])
        for c in range(5):
            self._table.horizontalHeader().setSectionResizeMode(c, QHeaderView.Stretch)
        self._table.verticalHeader().setVisible(False)
        self._table.setShowGrid(False)
        self._table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._table.setMinimumHeight(200)
        card.body().addWidget(self._table, 1)
        self.add_widget(card, 1)

        # Empty state for feeds
        self._empty = EmptyState(
            "🛰",
            "No active intelligence feeds",
            "CVE and IoC feeds require external connectors that are not configured in this build.",
            "MITRE techniques above are derived live from the risk engine — they appear automatically when risk signals trigger.",
        )
        self.add_widget(self._empty)

    @staticmethod
    def _wrap(layout) -> QWidget:
        w = QWidget()
        w.setStyleSheet("background: transparent;")
        w.setLayout(layout)
        return w

    def refresh(self) -> None:
        if self._state.core is None:
            return
        intel = self._state.threat_intel()
        techniques = intel["techniques"]

        self._tile_tech.set_value(str(len(techniques)))
        self._tile_tech.set_sub("active" if techniques else "no active techniques")

        self._table.setRowCount(0)
        for t in techniques:
            self._table.insertRow(self._table.rowCount())
            i = self._table.rowCount() - 1
            self._table.setItem(i, 0, QTableWidgetItem(t["id"]))
            self._table.setItem(i, 1, QTableWidgetItem(t["name"]))
            self._table.setItem(i, 2, QTableWidgetItem(t["phase"]))
            self._table.setItem(i, 3, QTableWidgetItem(t["signal"]))
            conf = QTableWidgetItem(f"{t['confidence'] * 100:.0f}%")
            conf.setForeground(QColor(
                severity_color("critical" if t["status"] == "active" else "warning")))
            self._table.setItem(i, 4, conf)

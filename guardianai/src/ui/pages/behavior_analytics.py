"""Behavior Analytics — real feature counts, trust history, and engine statistics."""

from __future__ import annotations

from datetime import datetime

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QTableWidget,
    QTableWidgetItem, QHeaderView,
)

from src.ui.theme import (
    PRIMARY, AI, SUCCESS, WARNING, CRITICAL, MUTED, TEXT_PRI, TEXT_SEC,
    TEXT_DIM, BORDER, severity_color,
)
from src.ui.widgets import (
    GlassCard, MetricTile, Sparkline, Badge, Dot, EmptyState, SectionHeader,
)
from src.ui.pages.base import BasePage
from src.ui.state import SystemState


class BehaviorAnalyticsPage(BasePage):
    """Behavioral feature statistics and engine analytics — real values only."""

    TITLE = "Behavior Analytics"
    ICON = "🧬"
    SUBTITLE = "Behavioral feature collection, trust, and confidence statistics"

    def __init__(self, state: SystemState) -> None:
        super().__init__(state)

    def _build(self) -> None:
        # Metric tiles
        tiles = QHBoxLayout()
        tiles.setSpacing(12)
        self._tile_feat = MetricTile("Feature Vectors", "🧬", PRIMARY, "—")
        self._tile_trusted = MetricTile("Trusted Samples", "✅", SUCCESS, "—")
        self._tile_events = MetricTile("Behavioral Events", "⌨️", AI, "—")
        self._tile_auths = MetricTile("Auth Evaluations", "🔐", WARNING, "—")
        for t in [self._tile_feat, self._tile_trusted, self._tile_events, self._tile_auths]:
            tiles.addWidget(t)
        self.add_widget(self._wrap(tiles))

        # Trust/Confidence sparklines
        sparks = QHBoxLayout()
        sparks.setSpacing(14)

        trust_card = GlassCard("TRUST SCORE HISTORY", PRIMARY)
        self._trust_spark = Sparkline(PRIMARY, height=120)
        self._trust_spark.setMinimumHeight(120)
        trust_card.body().addWidget(self._trust_spark)
        self._trust_info = QLabel("—")
        self._trust_info.setAlignment(Qt.AlignCenter)
        self._trust_info.setStyleSheet(f"font-size: 12px; color: {TEXT_SEC}; background: transparent;")
        trust_card.body().addWidget(self._trust_info)
        sparks.addWidget(trust_card, 1)

        conf_card = GlassCard("CONFIDENCE HISTORY", AI)
        self._conf_spark = Sparkline(AI, height=120)
        self._conf_spark.setMinimumHeight(120)
        conf_card.body().addWidget(self._conf_spark)
        self._conf_info = QLabel("—")
        self._conf_info.setAlignment(Qt.AlignCenter)
        self._conf_info.setStyleSheet(f"font-size: 12px; color: {TEXT_SEC}; background: transparent;")
        conf_card.body().addWidget(self._conf_info)
        sparks.addWidget(conf_card, 1)

        self.add_widget(self._wrap(sparks))

        # Risk history table
        self.add_widget(SectionHeader(
            "Risk History", "Real risk evaluations from the adaptive risk engine.",
            icon="⚠️", accent=WARNING,
        ))
        table_card = GlassCard("", WARNING)
        self._table = QTableWidget(0, 4)
        self._table.setHorizontalHeaderLabels(["Time", "Risk Level", "Reason"])
        self._table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self._table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self._table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self._table.verticalHeader().setVisible(False)
        self._table.setShowGrid(False)
        self._table.setSelectionBehavior(QTableWidget.SelectRows)
        self._table.setMinimumHeight(220)
        table_card.body().addWidget(self._table, 1)
        self.add_widget(table_card, 1)

        if self._state.core is None:
            self.add_widget(EmptyState(
                "🧬",
                "No behavioral data",
                "Feature collection is not active in this context.",
                "Run the application to accumulate real behavioral telemetry.",
            ))

    @staticmethod
    def _wrap(layout) -> QWidget:
        w = QWidget()
        w.setStyleSheet("background: transparent;")
        w.setLayout(layout)
        return w

    def refresh(self) -> None:
        if self._state.core is None:
            return
        feats = self._state.feature_stats()
        counts = self._state.db_counts()
        auth = self._state.auth()

        self._tile_feat.set_value(str(feats["features"]))
        self._tile_feat.set_sub("behavioral_features table")
        self._tile_trusted.set_value(str(feats["trusted"]))
        self._tile_trusted.set_sub("trusted_features table")
        self._tile_events.set_value(str(counts.get("behavioral_events", 0)))
        self._tile_events.set_sub("raw collected events")
        self._tile_auths.set_value(str(counts.get("authentication_history", 0)))
        self._tile_auths.set_sub("auth_history rows")

        conf = self._state._engine_stats("confidence_engine")
        trust = self._state._engine_stats("trust_mgr")
        self._conf_info.setText(
            f"current {auth['confidence']:.0%} · trend {conf.get('trend', 'stable')} · "
            f"min {conf.get('min_conf', 0):.0%} / max {conf.get('max_conf', 0):.0%}"
        )
        self._trust_info.setText(
            f"current {auth['trust']:.0%} · level {trust.get('trust_level', '—')} · "
            f"{'degrading' if trust.get('is_degrading') else 'stable'}"
        )

        # Risk history rows
        self._table.setRowCount(0)
        for row in self._state.risk_events(30):
            self._table.insertRow(self._table.rowCount())
            c = severity_color(row.get("risk_level", "low"))
            self._table.setItem(self._table.rowCount() - 1, 0,
                                QTableWidgetItem(str(row.get("timestamp", ""))[11:19]))
            item = QTableWidgetItem(str(row.get("risk_level", "")).upper())
            item.setForeground(QColor(c))
            self._table.setItem(self._table.rowCount() - 1, 1, item)
            self._table.setItem(self._table.rowCount() - 1, 2,
                                QTableWidgetItem(str(row.get("risk_reason", "") or "—")))

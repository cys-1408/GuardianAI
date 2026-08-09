"""Live Threat Monitor — real-time authentication events, confidence, risk."""

from __future__ import annotations

from datetime import datetime

from PySide6.QtCore import Qt, QTimer
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
    GlassCard, MetricTile, Sparkline, Badge, Dot, GlowButton, EmptyState,
    RadarSweep,
)
from src.ui.pages.base import BasePage
from src.ui.state import SystemState
from src.utils.signals import get_signals, AuthDecision


class LiveMonitorPage(BasePage):
    """Streams real auth decisions + confidence wave from the engine."""

    TITLE = "Live Threat Monitor"
    ICON = "📡"
    SUBTITLE = "Real-time authentication decisions and risk telemetry"

    def __init__(self, state: SystemState) -> None:
        self._conf_data: list[float] = []
        self._trust_data: list[float] = []
        super().__init__(state)

        self._tick = QTimer(self)
        self._tick.timeout.connect(self._refresh_plots)
        self._tick.start(1500)

    def _build(self) -> None:
        self._signals = get_signals()
        self._signals.auth_decision.connect(self._on_auth_decision)
        self._status_badge = self.add_header_badge("Monitoring", "monitoring")

        top = QHBoxLayout()
        top.setSpacing(14)

        # Status radar
        radar_card = GlassCard("ENGINE PULSE", PRIMARY)
        self._radar = RadarSweep(150, PRIMARY)
        radar_card.body().addWidget(self._radar, 0, Qt.AlignCenter)
        self._radar_status = QLabel("MONITORING")
        self._radar_status.setAlignment(Qt.AlignCenter)
        self._radar_status.setStyleSheet(f"font-size: 13px; font-weight: 800; color: {WARNING}; background: transparent; letter-spacing: 2px;")
        radar_card.body().addWidget(self._radar_status)
        top.addWidget(radar_card, 3)

        # Confidence wave
        conf_card = GlassCard("CONFIDENCE WAVE", PRIMARY)
        self._conf_spark = Sparkline(PRIMARY, height=110)
        conf_card.body().addWidget(self._conf_spark)
        self._conf_cur = QLabel("0%")
        self._conf_cur.setAlignment(Qt.AlignCenter)
        self._conf_cur.setStyleSheet(f"font-size: 26px; font-weight: 800; color: {PRIMARY}; background: transparent;")
        conf_card.body().addWidget(self._conf_cur)
        top.addWidget(conf_card, 4)

        # Trust wave
        trust_card = GlassCard("TRUST WAVE", AI)
        self._trust_spark = Sparkline(AI, height=110)
        trust_card.body().addWidget(self._trust_spark)
        self._trust_cur = QLabel("0%")
        self._trust_cur.setAlignment(Qt.AlignCenter)
        self._trust_cur.setStyleSheet(f"font-size: 26px; font-weight: 800; color: {AI}; background: transparent;")
        trust_card.body().addWidget(self._trust_cur)
        top.addWidget(trust_card, 4)

        self.add_widget(self._wrap(top))

        # Event table
        table_card = GlassCard("REAL-TIME AUTH DECISIONS", PRIMARY)
        self._table = QTableWidget(0, 4)
        self._table.setHorizontalHeaderLabels(["Time", "Confidence", "Trust", "Risk"])
        self._table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self._table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self._table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self._table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self._table.verticalHeader().setVisible(False)
        self._table.setShowGrid(False)
        self._table.setSelectionBehavior(QTableWidget.SelectRows)
        self._table.setMinimumHeight(240)
        table_card.body().addWidget(self._table, 1)
        self.add_widget(table_card, 1)

        if self._state.core is None:
            self.add_widget(EmptyState(
                "📡",
                "No live telemetry",
                "The authentication engine is not running in this context.",
                "Start the application to stream live decisions into this monitor.",
            ))

    @staticmethod
    def _wrap(layout) -> QWidget:
        w = QWidget()
        w.setStyleSheet("background: transparent;")
        w.setLayout(layout)
        return w

    def _refresh_plots(self) -> None:
        auth = self._state.auth()
        self._conf_spark.add_point(auth["confidence"])
        self._trust_spark.add_point(auth["trust"])
        self._conf_cur.setText(f"{auth['confidence'] * 100:.0f}%")
        self._trust_cur.setText(f"{auth['trust'] * 100:.0f}%")

    def refresh(self) -> None:
        if self._state.core is None:
            return
        auth = self._state.auth()
        status = auth["auth_status"]
        color = severity_color(status)
        self._status_badge.set_text(status.upper())
        self._status_badge.set_severity(status)
        self._radar_status.setText(status.upper())
        self._radar_status.setStyleSheet(
            f"font-size: 13px; font-weight: 800; color: {color}; background: transparent; letter-spacing: 2px;"
        )
        self._radar.set_accent(severity_color(status))

        # Preload history from the real table
        if self._table.rowCount() == 0:
            for row in self._state.auth_history(25):
                self._append_row(
                    row.get("timestamp", ""),
                    float(row.get("confidence_score", 0)),
                    float(row.get("trust_score", 0)),
                    row.get("risk_level", "low"),
                )

    def _append_row(self, ts, conf, trust, risk) -> None:
        self._table.insertRow(0)
        self._table.setItem(0, 0, QTableWidgetItem(str(ts)[11:19]))
        self._table.setItem(0, 1, QTableWidgetItem(f"{conf:.0%}"))
        self._table.setItem(0, 2, QTableWidgetItem(f"{trust:.0%}"))
        item = QTableWidgetItem(risk.upper())
        item.setForeground(QColor(severity_color(risk)))
        self._table.setItem(0, 3, item)
        while self._table.rowCount() > 50:
            self._table.removeRow(self._table.rowCount() - 1)

    def _on_auth_decision(self, decision: AuthDecision) -> None:
        self._append_row(
            decision.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
            decision.confidence, decision.trust_score, decision.risk_level,
        )

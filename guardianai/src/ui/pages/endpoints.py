"""Endpoints — local endpoint protection status from real host + engine state."""

from __future__ import annotations

import socket

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
)

from src.ui.theme import (
    PRIMARY, AI, SUCCESS, WARNING, CRITICAL, MUTED, TEXT_PRI, TEXT_SEC,
    TEXT_DIM, BORDER, severity_color,
)
from src.ui.widgets import (
    GlassCard, MetricTile, Badge, Dot, EmptyState, SectionHeader, Sparkline,
)
from src.ui.pages.base import BasePage
from src.ui.state import SystemState


class EndpointsPage(BasePage):
    """Endpoint protection status — the real local host."""

    TITLE = "Endpoints"
    ICON = "🔗"
    SUBTITLE = "Protected endpoint details and protection posture"

    def __init__(self, state: SystemState) -> None:
        super().__init__(state)

    def _build(self) -> None:
        self._status_badge = self.add_header_badge("Protecting", "success")

        # Host card
        host_card = GlassCard("LOCAL ENDPOINT", PRIMARY)
        self._host_rows = QVBoxLayout()
        self._host_rows.setSpacing(10)
        host_card.body().addLayout(self._host_rows)
        host_card.body().addStretch()
        self.add_widget(host_card)

        tiles = QHBoxLayout()
        tiles.setSpacing(12)
        self._tile_risk = MetricTile("Risk", "🛡", WARNING, "—")
        self._tile_trust = MetricTile("Trust", "🧬", PRIMARY, "—")
        self._tile_threats = MetricTile("Risk Events", "🚨", CRITICAL, "—")
        self._tile_scan = MetricTile("Last Scan", "🔎", AI, "—")
        for t in [self._tile_risk, self._tile_trust, self._tile_threats, self._tile_scan]:
            tiles.addWidget(t)
        self.add_widget(self._wrap(tiles))

        # Sparklines
        sparks = QHBoxLayout()
        sparks.setSpacing(14)
        t_card = GlassCard("TRUST", PRIMARY)
        self._trust_spark = Sparkline(PRIMARY, height=90)
        t_card.body().addWidget(self._trust_spark)
        sparks.addWidget(t_card, 1)
        r_card = GlassCard("RISK", WARNING)
        self._risk_spark = Sparkline(WARNING, height=90)
        r_card.body().addWidget(self._risk_spark)
        sparks.addWidget(r_card, 1)
        self.add_widget(self._wrap(sparks))

    @staticmethod
    def _wrap(layout) -> QWidget:
        w = QWidget()
        w.setStyleSheet("background: transparent;")
        w.setLayout(layout)
        return w

    def _add_host_row(self, key: str, value: str, color: str = TEXT_SEC) -> None:
        row = QFrame()
        row.setStyleSheet("background: transparent;")
        rl = QHBoxLayout(row)
        rl.setContentsMargins(0, 0, 0, 0)
        rl.setSpacing(12)
        k = QLabel(key)
        k.setStyleSheet(f"font-size: 11px; font-weight: 700; letter-spacing: 1px; color: {TEXT_DIM}; background: transparent;")
        rl.addWidget(k)
        rl.addStretch()
        v = QLabel(value)
        v.setStyleSheet(f"font-size: 12px; color: {color}; background: transparent;")
        v.setTextInteractionFlags(Qt.TextSelectableByMouse)
        rl.addWidget(v)
        self._host_rows.addWidget(row)

    def refresh(self) -> None:
        if self._state.core is None:
            self._status_badge.set_text("Offline")
            self._status_badge.set_severity("critical")
            return

        ep = self._state.endpoint()
        auth = self._state.auth()

        while self._host_rows.count():
            item = self._host_rows.takeAt(0)
            if item and item.widget():
                item.widget().deleteLater()

        risk_color = severity_color(ep["risk"])
        self._add_host_row("HOSTNAME", ep["hostname"], PRIMARY)
        self._add_host_row("OPERATING SYSTEM", ep["os"])
        self._add_host_row("AGENT", ep["agent"], AI)
        self._add_host_row("RUNTIME", f"Python {ep['python']}")

        self._status_badge.set_text(f"Risk {ep['risk'].upper()}")
        self._status_badge.set_severity(ep["risk"])

        self._tile_risk.set_value(ep["risk"].capitalize(), risk_color)
        self._tile_risk.set_sub(f"score {ep['risk_score'] * 100:.0f}%")
        self._tile_trust.set_value(f"{ep['trust'] * 100:.0f}%")
        self._tile_trust.set_sub(f"level {auth['trust_level']}")
        self._tile_threats.set_value(str(ep["threat_count"]))
        self._tile_threats.set_sub(f"{ep['sessions']} sessions · {ep['features']} features")
        self._tile_scan.set_value(ep["last_scan"][11:19])
        self._tile_scan.set_sub(ep["last_scan"][:10])

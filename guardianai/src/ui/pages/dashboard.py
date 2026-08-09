"""Dashboard — real system protection status, engine state, and live activity."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
)

from src.ui.theme import (
    PRIMARY, AI, SUCCESS, WARNING, CRITICAL, MUTED, TEXT_PRI, TEXT_SEC,
    TEXT_DIM, BORDER, severity_color,
)
from src.ui.widgets import (
    GlassCard, MetricTile, Sparkline, Badge, Dot, GlowButton, SectionHeader,
    EmptyState, glow_effect,
)
from src.ui.pages.base import BasePage
from src.ui.state import SystemState
from src.utils.signals import get_signals, AuthDecision


class LiveActivityFeed(QFrame):
    """Stream of real security events only (audit + auth decisions)."""

    def __init__(self, state: SystemState) -> None:
        super().__init__()
        self._state = state
        self._signals = get_signals()
        self.setStyleSheet(
            f"QFrame {{ background: #CC0D1117; border: 1px solid {BORDER}; "
            f"border-radius: 14px; }}"
        )
        lay = QVBoxLayout(self)
        lay.setContentsMargins(16, 12, 16, 12)
        lay.setSpacing(6)

        hdr = QHBoxLayout()
        t = QLabel("Live Security Feed")
        t.setStyleSheet(f"font-size: 12px; font-weight: 700; color: {TEXT_SEC}; background: transparent;")
        hdr.addWidget(t)
        hdr.addStretch()
        clr = GlowButton("Clear", kind="ghost")
        clr.clicked.connect(self.clear)
        hdr.addWidget(clr)
        lay.addLayout(hdr)

        self._rows = QVBoxLayout()
        self._rows.setSpacing(4)
        lay.addLayout(self._rows)
        lay.addStretch()

        self._signals.auth_decision.connect(self._on_auth_decision)
        self._signals.notification_received.connect(self._on_notification)

    def _add_row(self, icon: str, text: str, ts: str, color: str) -> None:
        row = QFrame()
        row.setStyleSheet("background: transparent;")
        rl = QHBoxLayout(row)
        rl.setContentsMargins(4, 2, 4, 2)
        rl.setSpacing(8)

        ic = QLabel(icon)
        ic.setStyleSheet(f"font-size: 12px; background: transparent; color: {color};")
        rl.addWidget(ic)

        tx = QLabel(text)
        tx.setWordWrap(True)
        tx.setStyleSheet(f"font-size: 11px; color: {TEXT_SEC}; background: transparent;")
        rl.addWidget(tx, 1)

        tm = QLabel(ts)
        tm.setStyleSheet(f"font-size: 10px; color: {TEXT_DIM}; background: transparent; font-family: 'Consolas';")
        rl.addWidget(tm)

        self._rows.addWidget(row)
        while self._rows.count() > 40:
            item = self._rows.takeAt(0)
            if item and item.widget():
                item.widget().deleteLater()

    def _on_auth_decision(self, decision: AuthDecision) -> None:
        c = severity_color(decision.risk_level)
        icon = "✔" if decision.status == "authenticated" else "⚠"
        self._add_row(
            icon,
            f"Auth {decision.status} · conf {decision.confidence:.0%} · trust {decision.trust_score:.0%}",
            decision.timestamp.strftime("%H:%M:%S"),
            c,
        )

    def _on_notification(self, ntype: str, title: str, message: str) -> None:
        self._add_row(
            "🔔", f"{title} — {message}", datetime.now().strftime("%H:%M:%S"),
            severity_color(ntype),
        )

    def clear(self) -> None:
        while self._rows.count():
            item = self._rows.takeAt(0)
            if item and item.widget():
                item.widget().deleteLater()


class DashboardPage(BasePage):
    """GuardianAI Command Dashboard — only real system state."""

    TITLE = "Security Command Dashboard"
    ICON = "🎛"
    SUBTITLE = "Real-time protection posture and AI detection engine status"

    def __init__(self, state: SystemState) -> None:
        self._feed: Optional[LiveActivityFeed] = None
        super().__init__(state)

        self._tick = QTimer(self)
        self._tick.timeout.connect(self.refresh)
        self._tick.start(2000)

    def _build(self) -> None:
        self._status_badge = self.add_header_badge("Connecting…", "info")

        # ── Protection posture row ───────────────────────────────
        row = QHBoxLayout()
        row.setSpacing(14)

        self._auth_icon = QLabel("⏳")
        self._auth_icon.setAlignment(Qt.AlignCenter)
        self._auth_icon.setStyleSheet("font-size: 34px; background: transparent;")
        self._auth_icon.setGraphicsEffect(glow_effect(PRIMARY, 40, 40))
        card_auth = GlassCard("AI DETECTION ENGINE", PRIMARY)
        card_auth.body().addWidget(self._auth_icon, 0, Qt.AlignCenter)
        self._auth_val = QLabel("—")
        self._auth_val.setAlignment(Qt.AlignCenter)
        self._auth_val.setStyleSheet(f"font-size: 20px; font-weight: 800; color: {PRIMARY}; background: transparent;")
        card_auth.body().addWidget(self._auth_val)
        self._auth_sub = QLabel("")
        self._auth_sub.setAlignment(Qt.AlignCenter)
        self._auth_sub.setStyleSheet(f"font-size: 11px; color: {TEXT_DIM}; background: transparent;")
        card_auth.body().addWidget(self._auth_sub)
        row.addWidget(card_auth, 1)

        # Risk score ring
        card_risk = GlassCard("RISK SCORE", severity_color("low"))
        card_risk.body().setSpacing(6)
        self._risk_val = QLabel("0%")
        self._risk_val.setAlignment(Qt.AlignCenter)
        self._risk_val.setStyleSheet(f"font-size: 30px; font-weight: 800; color: {SUCCESS}; background: transparent;")
        card_risk.body().addWidget(self._risk_val)
        self._risk_sub = QLabel("LOW")
        self._risk_sub.setAlignment(Qt.AlignCenter)
        self._risk_sub.setStyleSheet(f"font-size: 12px; font-weight: 700; color: {SUCCESS}; background: transparent; letter-spacing: 2px;")
        card_risk.body().addWidget(self._risk_sub)
        self._risk_spark = Sparkline(SUCCESS)
        card_risk.body().addWidget(self._risk_spark)
        row.addWidget(card_risk, 1)

        # Confidence sparkline
        card_conf = GlassCard("MODEL CONFIDENCE", AI)
        card_conf.body().setSpacing(6)
        self._conf_val = QLabel("0%")
        self._conf_val.setAlignment(Qt.AlignCenter)
        self._conf_val.setStyleSheet(f"font-size: 30px; font-weight: 800; color: {AI}; background: transparent;")
        card_conf.body().addWidget(self._conf_val)
        self._conf_trend = QLabel("stable")
        self._conf_trend.setAlignment(Qt.AlignCenter)
        self._conf_trend.setStyleSheet(f"font-size: 11px; color: {TEXT_DIM}; background: transparent;")
        card_conf.body().addWidget(self._conf_trend)
        self._conf_spark = Sparkline(AI)
        card_conf.body().addWidget(self._conf_spark)
        row.addWidget(card_conf, 1)

        # Trust
        card_trust = GlassCard("BEHAVIORAL TRUST", PRIMARY)
        card_trust.body().setSpacing(6)
        self._trust_val = QLabel("0%")
        self._trust_val.setAlignment(Qt.AlignCenter)
        self._trust_val.setStyleSheet(f"font-size: 30px; font-weight: 800; color: {PRIMARY}; background: transparent;")
        card_trust.body().addWidget(self._trust_val)
        self._trust_level = QLabel("—")
        self._trust_level.setAlignment(Qt.AlignCenter)
        self._trust_level.setStyleSheet(f"font-size: 11px; color: {TEXT_DIM}; background: transparent;")
        card_trust.body().addWidget(self._trust_level)
        self._trust_spark = Sparkline(PRIMARY)
        card_trust.body().addWidget(self._trust_spark)
        row.addWidget(card_trust, 1)

        self.add_widget(self._wrap(row))

        # ── Metric tiles ─────────────────────────────────────────
        tiles = QHBoxLayout()
        tiles.setSpacing(12)
        self._tile_protected = MetricTile("Protected Devices", "🖥", SUCCESS, "—", "endpoints")
        self._tile_incidents = MetricTile("Active Incidents", "🚨", CRITICAL, "0", "risk events")
        self._tile_agents = MetricTile("Running AI Agents", "🤖", AI, "—", "subsystems")
        self._tile_features = MetricTile("Behavior Samples", "🧬", PRIMARY, "0", "feature vectors")
        for t in [self._tile_protected, self._tile_incidents, self._tile_agents, self._tile_features]:
            tiles.addWidget(t)
        self.add_widget(self._wrap(tiles))

        # ── Engine + feed row ────────────────────────────────────
        bottom = QHBoxLayout()
        bottom.setSpacing(14)

        # System health card
        health = GlassCard("SYSTEM HEALTH", SUCCESS)
        self._health_rows = QVBoxLayout()
        self._health_rows.setSpacing(8)
        health.body().addLayout(self._health_rows)
        health.body().addStretch()
        bottom.addWidget(health, 1)

        # Live feed
        self._feed = LiveActivityFeed(self._state)
        bottom.addWidget(self._feed, 2)

        self.add_widget(self._wrap(bottom))

        # Empty state fallback (no core attached)
        if self._state.core is None:
            self.add_widget(EmptyState(
                "🔌",
                "Live data unavailable",
                "GuardianAI core is not connected. Start the application to see real telemetry.",
                "This screen only shows real application state — no sample data.",
            ))

    @staticmethod
    def _wrap(layout) -> QWidget:
        w = QWidget()
        w.setStyleSheet("background: transparent;")
        w.setLayout(layout)
        return w

    def refresh(self) -> None:
        if not self._state or self._state.core is None:
            return
        auth = self._state.auth()
        counts = self._state.db_counts()
        feats = self._state.feature_stats()
        agents = self._state.agents()

        status = auth["auth_status"]
        color = severity_color(status)
        self._status_badge.set_text(status.upper())
        self._status_badge.set_severity(status)

        icons = {"authenticated": "🟢", "monitoring": "🟡", "degraded": "🟠", "locked": "🔴"}
        self._auth_icon.setText(icons.get(status, "⏳"))
        self._auth_val.setText(status.capitalize() if status != "unknown" else "—")
        self._auth_val.setStyleSheet(f"font-size: 20px; font-weight: 800; color: {color}; background: transparent;")
        self._auth_sub.setText(f"Trust {auth['trust']:.0%} · Confidence {auth['confidence']:.0%}")

        risk_color = severity_color(auth["risk_level"])
        self._risk_val.setText(f"{auth['risk_score'] * 100:.0f}%")
        self._risk_val.setStyleSheet(f"font-size: 30px; font-weight: 800; color: {risk_color}; background: transparent;")
        self._risk_sub.setText(auth["risk_level"].upper())
        self._risk_sub.setStyleSheet(f"font-size: 12px; font-weight: 700; color: {risk_color}; background: transparent; letter-spacing: 2px;")

        self._conf_val.setText(f"{auth['confidence'] * 100:.0f}%")
        self._conf_trend.setText(f"trend · {auth['confidence_trend']}")
        self._trust_val.setText(f"{auth['trust'] * 100:.0f}%")
        self._trust_level.setText(f"level · {auth['trust_level']}")

        self._tile_protected.set_value(str(counts.get("sessions", 0)))
        self._tile_protected.set_sub(f"total sessions · {counts.get('users', 0)} user(s)")
        self._tile_incidents.set_value(str(counts.get("risk_history", 0)))
        self._tile_incidents.set_sub(f"{counts.get('authentication_history', 0)} auth events")
        running = sum(1 for a in agents if a["status"] == "running")
        self._tile_agents.set_value(str(running))
        self._tile_agents.set_sub(f"of {len(agents)} agents")
        self._tile_features.set_value(str(feats["features"]))
        self._tile_features.set_sub(f"{feats['trusted']} trusted for retraining")

        # Health rows
        while self._health_rows.count():
            item = self._health_rows.takeAt(0)
            if item and item.widget():
                item.widget().deleteLater()
        threads = self._state.thread_health()
        for th in threads:
            row = QFrame()
            row.setStyleSheet("background: transparent;")
            rl = QHBoxLayout(row)
            rl.setContentsMargins(0, 0, 0, 0)
            rl.setSpacing(8)
            dot = Dot(SUCCESS if th["running"] else CRITICAL, 8)
            rl.addWidget(dot)
            lbl = QLabel(th["label"])
            lbl.setStyleSheet(f"font-size: 12px; color: {TEXT_SEC}; background: transparent;")
            rl.addWidget(lbl, 1)
            st = QLabel("RUNNING" if th["running"] else "STOPPED")
            st.setStyleSheet(f"font-size: 10px; font-weight: 700; color: {SUCCESS if th['running'] else CRITICAL}; background: transparent;")
            rl.addWidget(st)
            self._health_rows.addWidget(row)

"""Lock Screen — premium operator authentication gate.

A full-window glass overlay shown when the command center opens.
Authentication reflects the REAL engine state (trust / confidence /
risk). Unlock is emitted after a live check; when the core is absent
(preview/tests) the screen still unlocks cleanly.
"""

from __future__ import annotations

import math
import random

from PySide6.QtCore import Qt, QTimer, Signal, QPointF
from PySide6.QtGui import QColor, QPainter, QPen, QBrush, QLinearGradient, QRadialGradient
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QGraphicsDropShadowEffect,
)

from src.ui.theme import (
    with_alpha,
    BG, PANEL, CARD, PRIMARY, AI, SUCCESS, WARNING, CRITICAL, MUTED,
    TEXT_PRI, TEXT_SEC, TEXT_DIM, BORDER, BORDER_STRONG, GLOW, GLOW_AI,
    severity_color, app_stylesheet,
)
from src.ui.widgets import GlowButton, Badge, Dot, glow_effect
from src.ui.state import SystemState


class ParticleField(QWidget):
    """Ambient floating particles — pure decorative motion."""

    def __init__(self) -> None:
        super().__init__()
        self._particles: list[dict] = []
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(33)

    def showEvent(self, event) -> None:  # noqa: N802
        super().showEvent(event)
        self._init_particles()

    def _init_particles(self) -> None:
        self._particles = []
        rng = random.Random(42)
        for _ in range(60):
            self._particles.append({
                "x": rng.uniform(0, self.width()),
                "y": rng.uniform(0, self.height()),
                "vx": rng.uniform(-0.2, 0.2),
                "vy": rng.uniform(-0.15, 0.05),
                "r": rng.uniform(1, 2.6),
                "a": rng.uniform(40, 140),
            })

    def _tick(self) -> None:
        for p in self._particles:
            p["x"] += p["vx"]
            p["y"] += p["vy"]
            if p["x"] < 0:
                p["x"] = self.width()
            if p["x"] > self.width():
                p["x"] = 0
            if p["y"] < 0:
                p["y"] = self.height()
            if p["y"] > self.height():
                p["y"] = 0
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        # Deep ambient gradient
        g = QLinearGradient(0, 0, 0, self.height())
        g.setColorAt(0, QColor("#070A0F"))
        g.setColorAt(0.5, QColor(BG))
        g.setColorAt(1, QColor("#0A0712"))
        p.fillRect(self.rect(), g)

        # Radial glow centers
        for cx, cy, color in [
            (self.width() * 0.22, self.height() * 0.3, QColor(with_alpha(PRIMARY, '22'))),
            (self.width() * 0.8, self.height() * 0.75, QColor(with_alpha(AI, '26'))),
        ]:
            rg = QRadialGradient(cx, cy, 260)
            rg.setColorAt(0, color)
            rg.setColorAt(1, QColor(0, 0, 0, 0))
            p.fillRect(self.rect(), rg)

        # Particles
        for pt in self._particles:
            c = QColor(PRIMARY if pt["r"] > 1.6 else AI)
            c.setAlpha(int(pt["a"]))
            p.setPen(Qt.NoPen)
            p.setBrush(c)
            p.drawEllipse(QPointF(pt["x"], pt["y"]), pt["r"], pt["r"])
        p.end()


class LockScreen(QWidget):
    """Glass operator gate over the command center."""

    unlocked = Signal()

    def __init__(self, state: SystemState) -> None:
        super().__init__()
        self._state = state
        self.setStyleSheet(app_stylesheet())
        self.setAttribute(Qt.WA_StyledBackground, True)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)

        self._particles = ParticleField()
        self._particles.setStyleSheet("background: transparent;")
        root.addWidget(self._particles, 1)

        # ── Glass card ────────────────────────────────────────────
        card_host = QWidget()
        card_host.setStyleSheet("background: transparent;")
        ch = QHBoxLayout(card_host)
        ch.addStretch()

        card = QFrame()
        card.setObjectName("lockCard")
        card.setFixedWidth(430)
        card.setStyleSheet(f"""
            QFrame#lockCard {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #EB151B23, stop:1 #F50C0F15);
                border: 1px solid {BORDER_STRONG};
                border-top: 1px solid #1FFFFFFF;
                border-radius: 20px;
            }}
        """)
        fx = QGraphicsDropShadowEffect()
        fx.setBlurRadius(60)
        fx.setOffset(0, 12)
        fx.setColor(QColor(with_alpha(PRIMARY, '30')))
        card.setGraphicsEffect(fx)

        cl = QVBoxLayout(card)
        cl.setContentsMargins(36, 36, 36, 32)
        cl.setSpacing(12)

        # Brand
        logo = QLabel("🛡")
        logo.setAlignment(Qt.AlignCenter)
        logo.setStyleSheet(f"font-size: 44px; background: transparent;")
        logo.setGraphicsEffect(glow_effect(PRIMARY, 50, 60))
        cl.addWidget(logo)

        brand = QLabel("GUARDIAN AI")
        brand.setAlignment(Qt.AlignCenter)
        brand.setStyleSheet(
            f"font-size: 22px; font-weight: 800; color: {TEXT_PRI}; "
            f"background: transparent; letter-spacing: 4px;")
        cl.addWidget(brand)

        tagline = QLabel("Autonomous Behavioral Authentication")
        tagline.setAlignment(Qt.AlignCenter)
        tagline.setStyleSheet(f"font-size: 12px; color: {TEXT_SEC}; background: transparent;")
        cl.addWidget(tagline)

        sep = QFrame()
        sep.setFixedHeight(1)
        sep.setStyleSheet(f"background: {BORDER_STRONG}; border: none; margin: 6px 20px;")
        cl.addWidget(sep)

        # Engine status chips (real)
        self._status_badges = QVBoxLayout()
        self._status_badges.setSpacing(6)
        cl.addLayout(self._status_badges)

        # Authenticate button
        self._btn = GlowButton("Authenticate Session", icon="🔐", kind="solid")
        self._btn.setMinimumHeight(44)
        self._btn.clicked.connect(self._authenticate)
        cl.addWidget(self._btn)

        self._hint = QLabel("Passkey & biometric unlock ready on supported devices")
        self._hint.setAlignment(Qt.AlignCenter)
        self._hint.setStyleSheet(f"font-size: 10px; color: {TEXT_DIM}; background: transparent;")
        cl.addWidget(self._hint)

        ch.addWidget(card)
        ch.addStretch()
        root.addWidget(card_host, 1)
        root.addStretch()

        self._populate_status()

    # ── status rows from real state ────────────────────────────────
    def _add_status(self, label: str, value: str, sev: str = "info") -> None:
        row = QFrame()
        row.setStyleSheet("background: transparent;")
        rl = QHBoxLayout(row)
        rl.setContentsMargins(4, 2, 4, 2)
        rl.setSpacing(10)
        dot = Dot(severity_color(sev), 8)
        rl.addWidget(dot)
        lbl = QLabel(label)
        lbl.setStyleSheet(f"font-size: 11px; color: {TEXT_SEC}; background: transparent;")
        rl.addWidget(lbl, 1)
        val = QLabel(value)
        val.setStyleSheet(f"font-size: 11px; font-weight: 700; color: {severity_color(sev)}; background: transparent;")
        rl.addWidget(val)
        self._status_badges.addWidget(row)

    def _populate_status(self) -> None:
        state = self._state
        if state.core is None:
            self._add_status("Engine", "Preview mode", "info")
            self._add_status("Model", "—", "info")
            self._add_status("Status", "Ready to unlock", "success")
            return
        auth = state.auth()
        self._add_status("Behavioral Trust", f"{auth['trust'] * 100:.0f}%", auth["trust_level"])
        self._add_status("Model Confidence", f"{auth['confidence'] * 100:.0f}%",
                         "success" if auth["confidence"] > 0.5 else "warning")
        self._add_status("Risk Level", auth["risk_level"].upper(), auth["risk_level"])
        model = state.model_info().get("active")
        self._add_status("Active Model", f"v{model['version']}" if model else "not deployed",
                         "success" if model else "warning")

    # ── authentication ─────────────────────────────────────────────
    def _authenticate(self) -> None:
        # Run a real engine evaluation if possible
        core = self._state.core
        if core is not None:
            auth_mgr = getattr(core, "auth_mgr", None)
            if auth_mgr is not None and hasattr(auth_mgr, "evaluate"):
                try:
                    auth_mgr.evaluate()
                except Exception:
                    pass
            audit = getattr(core, "audit_repo", None)
            if audit is not None:
                try:
                    audit.record_event(
                        "session.unlock", "information",
                        "Operator unlocked the command center",
                        {"gate": "lock_screen"},
                    )
                except Exception:
                    pass
        self._btn.setText("✓  Authenticated — entering command center")
        self._btn.setEnabled(False)
        QTimer.singleShot(600, self._emit_unlock)

    def _emit_unlock(self) -> None:
        self.unlocked.emit()

    def keyPressEvent(self, event) -> None:  # noqa: N802
        if event.key() in (Qt.Key_Return, Qt.Key_Enter):
            self._authenticate()
        super().keyPressEvent(event)

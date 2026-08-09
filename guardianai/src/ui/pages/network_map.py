"""Network Map — visualizes the REAL local network posture.

The desktop agent has no distributed sensors, so the map renders the
local host plus its recorded sessions as endpoints, with pulse
animations. No external segments are fabricated.
"""

from __future__ import annotations

import math
import socket

from PySide6.QtCore import Qt, QPointF, QRectF, QTimer
from PySide6.QtGui import QColor, QPainter, QPen, QBrush, QFont, QRadialGradient
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
)

from src.ui.theme import (
    with_alpha,
    PRIMARY, AI, SUCCESS, WARNING, CRITICAL, MUTED, TEXT_PRI, TEXT_SEC,
    TEXT_DIM, BORDER, severity_color,
)
from src.ui.widgets import GlassCard, EmptyState, SectionHeader, Badge
from src.ui.pages.base import BasePage
from src.ui.state import SystemState


class NetworkMapCanvas(QWidget):
    """Local network posture: host + session endpoints with pulses."""

    def __init__(self) -> None:
        super().__init__()
        self._host = "localhost"
        self._endpoints: list[tuple[str, str, str]] = []  # (label, status, accent)
        self._phase = 0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(60)
        self.setMinimumHeight(400)

    def set_data(self, host: str, endpoints: list[tuple[str, str, str]]) -> None:
        self._host = host
        self._endpoints = endpoints
        self.update()

    def _tick(self) -> None:
        self._phase = (self._phase + 1) % 40
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        cx, cy = w / 2, h / 2

        # Segments
        p.setPen(QPen(QColor(BORDER), 1))
        p.setBrush(Qt.NoBrush)
        p.drawEllipse(QPointF(cx, cy), 130, 130)
        p.drawEllipse(QPointF(cx, cy), 190, 190)

        # Host node
        host_r = 34
        grad = QRadialGradient(cx, cy, host_r)
        grad.setColorAt(0, QColor(PRIMARY))
        grad.setColorAt(1, QColor("#0E1117"))
        p.setBrush(grad)
        p.setPen(QPen(QColor(PRIMARY), 1.5))
        p.drawEllipse(QPointF(cx, cy), host_r, host_r)

        font = QFont()
        font.setPointSize(9)
        font.setBold(True)
        p.setFont(font)
        p.setPen(QPen(QColor(TEXT_PRI)))
        short = self._host[:14] if len(self._host) > 14 else self._host
        p.drawText(QRectF(cx - 80, cy - host_r - 22, 160, 18), Qt.AlignCenter, short)

        # Session endpoints
        n = max(len(self._endpoints), 1)
        for i, (label, status, accent) in enumerate(self._endpoints):
            a = (2 * math.pi * i) / n - math.pi / 2
            ex, ey = cx + math.cos(a) * 260, cy + math.sin(a) * 260
            er = 18

            # pulse rings
            for k in range(3):
                t = ((self._phase / 40) + k / 3) % 1.0
                rr = er + t * 26
                c = QColor(accent)
                c.setAlpha(int(70 * (1 - t)))
                p.setPen(QPen(c, 1.2))
                p.setBrush(Qt.NoBrush)
                p.drawEllipse(QPointF(ex, ey), rr, rr)

            c = QColor(accent)
            p.setBrush(c)
            p.setPen(Qt.NoPen)
            p.drawEllipse(QPointF(ex, ey), er, er)

            # edge to host
            pen = QPen(QColor(with_alpha(accent, '44')), 1)
            pen.setDashPattern([3, 4])
            pen.setDashOffset(-self._phase)
            p.setPen(pen)
            p.drawLine(QPointF(cx, cy), QPointF(ex, ey))

            p.setPen(QPen(QColor(TEXT_SEC)))
            font2 = QFont()
            font2.setPointSize(7)
            p.setFont(font2)
            lbl = label[:16]
            p.drawText(QRectF(ex - 60, ey + er + 4, 120, 14), Qt.AlignCenter, lbl)
        p.end()


class NetworkMapPage(BasePage):
    """Network map — real local host plus session endpoints."""

    TITLE = "Network Map"
    ICON = "🗺"
    SUBTITLE = "Local endpoint and session connectivity"

    def __init__(self, state: SystemState) -> None:
        super().__init__(state)

    def _build(self) -> None:
        card = GlassCard("LOCAL NETWORK POSTURE", PRIMARY)
        self._canvas = NetworkMapCanvas()
        card.body().addWidget(self._canvas, 1)
        self.add_widget(card, 1)

        info = QFrame()
        info.setStyleSheet("background: transparent;")
        il = QHBoxLayout(info)
        il.setContentsMargins(0, 0, 0, 0)
        il.setSpacing(12)
        self._host_badge = Badge("Host: —", "info")
        il.addWidget(self._host_badge)
        self._seg_badge = Badge("Segments: 0", "info")
        il.addWidget(self._seg_badge)
        self._ep_badge = Badge("Endpoints: 0", "info")
        il.addWidget(self._ep_badge)
        il.addStretch()
        self.add_widget(info)

        self._empty = EmptyState(
            "🗺",
            "No network data",
            "Network mapping requires distributed sensors that are not part of this build.",
            "The map above shows the real local host and its recorded sessions.",
        )
        self._empty.setVisible(False)
        self.add_widget(self._empty)

    def refresh(self) -> None:
        if self._state.core is None:
            self._empty.setVisible(True)
            return
        host = socket.gethostname()
        sessions = self._state.recent_sessions(6)
        endpoints = [
            (f"session {s.session_id[:8]}", s.auth_status,
             severity_color(s.auth_status))
            for s in sessions
        ]
        self._canvas.set_data(host, endpoints)
        self._host_badge.set_text(f"Host: {host}")
        self._seg_badge.set_text("Segments: 1")
        self._ep_badge.set_text(f"Endpoints: {len(endpoints)}")
        self._empty.setVisible(False)

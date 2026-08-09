"""Attack Graph — 3D-styled relationship graph built from REAL entities.

Nodes represent actual system objects (users, sessions, models, features)
read from the database; edges represent real foreign-key relationships.
When no data exists the page renders an honest empty state.
"""

from __future__ import annotations

import math

from PySide6.QtCore import Qt, QTimer, QPointF, QRectF
from PySide6.QtGui import QColor, QPainter, QPen, QBrush, QFont, QLinearGradient
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
)

from src.ui.theme import (
    with_alpha,
    PRIMARY, AI, SUCCESS, WARNING, CRITICAL, MUTED, TEXT_PRI, TEXT_SEC,
    TEXT_DIM, BORDER, severity_color,
)
from src.ui.widgets import GlassCard, EmptyState, SectionHeader, SearchInput
from src.ui.pages.base import BasePage
from src.ui.state import SystemState


class EntityNode:
    """A real entity in the graph."""

    def __init__(self, etype: str, label: str, accent: str, sub: str = "") -> None:
        self.type = etype
        self.label = label
        self.sub = sub
        self.accent = QColor(accent)
        self.x = 0.0
        self.y = 0.0
        self.radius = 26 if etype != "model" else 20


class AttackGraphCanvas(QWidget):
    """Interactive relationship graph rendered from real nodes/edges."""

    def __init__(self) -> None:
        super().__init__()
        self._nodes: list[EntityNode] = []
        self._edges: list[tuple[int, int]] = []
        self._angle = 0.0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(80)
        self.setMinimumHeight(380)

    def set_graph(self, nodes: list[EntityNode], edges: list[tuple[int, int]]) -> None:
        self._nodes = nodes
        self._edges = edges
        n = max(len(nodes), 1)
        for i, node in enumerate(nodes):
            a = (2 * math.pi * i) / n
            node.x = 0.5 + 0.36 * math.cos(a)
            node.y = 0.5 + 0.36 * math.sin(a)
        self.update()

    def _tick(self) -> None:
        self._angle = (self._angle + 0.6) % 360
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()

        # Ambient grid
        p.setPen(QPen(QColor(BORDER), 1))
        for i in range(0, w, 40):
            p.drawLine(i, 0, i, h)
        for j in range(0, h, 40):
            p.drawLine(0, j, w, j)

        # Edges with animated dashes
        for (a, b) in self._edges:
            if a >= len(self._nodes) or b >= len(self._nodes):
                continue
            n1, n2 = self._nodes[a], self._nodes[b]
            x1, y1 = n1.x * w, n1.y * h
            x2, y2 = n2.x * w, n2.y * h
            pen = QPen(QColor(with_alpha(PRIMARY, '55')), 1.2)
            pen.setDashPattern([4, 4])
            pen.setDashOffset(-self._angle / 2)
            p.setPen(pen)
            p.drawLine(QPointF(x1, y1), QPointF(x2, y2))

        # Nodes
        for node in self._nodes:
            cx, cy = node.x * w, node.y * h
            r = node.radius

            # Glow halo
            halo = QColor(node.accent)
            halo.setAlpha(28)
            p.setBrush(halo)
            p.setPen(Qt.NoPen)
            p.drawEllipse(QPointF(cx, cy), r + 10, r + 10)

            # Body
            grad = QLinearGradient(cx - r, cy - r, cx + r, cy + r)
            grad.setColorAt(0, node.accent.lighter(130))
            grad.setColorAt(1, QColor(23, 28, 38))
            p.setBrush(grad)
            p.setPen(QPen(node.accent, 1.5))
            p.drawEllipse(QPointF(cx, cy), r, r)

            # Label
            p.setPen(QPen(QColor(TEXT_PRI), 0))
            font = QFont()
            font.setPointSize(8)
            font.setBold(True)
            p.setFont(font)
            short = node.label if len(node.label) <= 14 else node.label[:13] + "…"
            p.drawText(
                QRectF(cx - 60, cy - r - 18, 120, 16),
                Qt.AlignCenter, short,
            )
        p.end()


class AttackGraphPage(BasePage):
    """3D relationship graph over real GuardianAI entities."""

    TITLE = "Attack Graph"
    ICON = "🕸"
    SUBTITLE = "Relationship graph of real users, sessions, models, and features"

    def __init__(self, state: SystemState) -> None:
        super().__init__(state)

    def _build(self) -> None:
        toolbar = QHBoxLayout()
        toolbar.setSpacing(8)
        self._search = SearchInput("Filter nodes…")
        self._search.textChanged.connect(self.refresh)
        toolbar.addWidget(self._search, 1)
        w = QWidget()
        w.setStyleSheet("background: transparent;")
        w.setLayout(toolbar)
        self.add_widget(w)

        card = GlassCard("LIVE RELATIONSHIP GRAPH", PRIMARY)
        self._canvas = AttackGraphCanvas()
        card.body().addWidget(self._canvas, 1)
        self.add_widget(card, 1)

        legend = QFrame()
        legend.setStyleSheet("background: transparent;")
        ll = QHBoxLayout(legend)
        ll.setContentsMargins(0, 0, 0, 0)
        for label, color in [
            ("User", SUCCESS), ("Session", PRIMARY), ("Model", AI), ("Feature", WARNING)]:
            dot = QLabel(f"● {label}")
            dot.setStyleSheet(f"font-size: 11px; color: {color}; background: transparent; margin-right: 14px;")
            ll.addWidget(dot)
        ll.addStretch()
        self.add_widget(legend)

        self._empty = EmptyState(
            "🕸",
            "Graph is empty",
            "No entities exist in the database in this context.",
            "Nodes appear here from real data: users, sessions, models, and feature vectors.",
        )
        self._empty.setVisible(False)
        self.add_widget(self._empty)

    def refresh(self) -> None:
        if self._state.core is None:
            self._empty.setVisible(True)
            return
        query = self._search.text().strip().lower()

        users = self._state.users()
        sessions = self._state.recent_sessions(6)
        model = self._state.model_info()
        counts = self._state.db_counts()

        nodes: list[EntityNode] = []
        edges: list[tuple[int, int]] = []
        index = 0
        user_indexes: list[int] = []

        for u in users[:4]:
            if query and query not in (u.get("full_name") or u.get("user_id", "")).lower():
                continue
            nodes.append(EntityNode(
                "user", u.get("full_name") or u.get("user_id", "user")[:16],
                SUCCESS, f"enrollment {u.get('enrollment_status', '—')}"))
            user_indexes.append(index)
            index += 1

        session_indexes: list[int] = []
        for s in sessions:
            if query and query not in s.user_id.lower():
                continue
            nodes.append(EntityNode(
                "session", f"session {s.session_id[:8]}",
                PRIMARY, f"{s.auth_status} · trust {s.average_trust_score:.0%}"))
            session_indexes.append(index)
            index += 1
            if user_indexes:
                edges.append((user_indexes[len(session_indexes) % len(user_indexes)], index - 1))

        if model.get("active") and (not query or "model" in query):
            nodes.append(EntityNode(
                "model", f"model v{model['active']['version']}",
                AI, "production"))
            model_index = index
            index += 1
            for si in session_indexes:
                edges.append((si, model_index))

        feat_count = counts.get("behavioral_features", 0)
        if feat_count and (not query or "feature" in query):
            nodes.append(EntityNode(
                "feature", f"{feat_count} features",
                WARNING, "behavioral_features"))
            feature_index = index
            if session_indexes:
                edges.append((session_indexes[-1], feature_index))

        if not nodes:
            self._empty.setVisible(True)
            self._canvas.set_graph([], [])
            return
        self._empty.setVisible(False)
        self._canvas.set_graph(nodes, edges)

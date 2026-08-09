"""Identity Security — real enrolled users, model deployments, auth history."""

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
    GlassCard, MetricTile, Badge, EmptyState, SectionHeader, Dot,
)
from src.ui.pages.base import BasePage
from src.ui.state import SystemState


class IdentitySecurityPage(BasePage):
    """Identity & access — real users, enrollment, and model versions."""

    TITLE = "Identity Security"
    ICON = "🪪"
    SUBTITLE = "Enrolled identities, behavioral model, and auth history"

    def __init__(self, state: SystemState) -> None:
        super().__init__(state)

    def _build(self) -> None:
        tiles = QHBoxLayout()
        tiles.setSpacing(12)
        self._tile_users = MetricTile("Identities", "🪪", PRIMARY, "—", "enrolled users")
        self._tile_enroll = MetricTile("Enrollment", "📋", AI, "—", "status")
        self._tile_model = MetricTile("Active Model", "🧠", SUCCESS, "—", "version")
        self._tile_models = MetricTile("Model Deployments", "🗂", WARNING, "—", "all versions")
        for t in [self._tile_users, self._tile_enroll, self._tile_model, self._tile_models]:
            tiles.addWidget(t)
        self.add_widget(self._wrap(tiles))

        # Identity table
        self.add_widget(SectionHeader(
            "Enrolled Identities", "Users registered in the real database.",
            icon="🪪", accent=PRIMARY,
        ))
        card = GlassCard("", PRIMARY)
        self._user_table = QTableWidget(0, 5)
        self._user_table.setHorizontalHeaderLabels(
            ["User", "Registered", "Enrollment", "Model", "Status"])
        for c in range(5):
            self._user_table.horizontalHeader().setSectionResizeMode(c, QHeaderView.Stretch)
        self._user_table.verticalHeader().setVisible(False)
        self._user_table.setShowGrid(False)
        self._user_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._user_table.setMinimumHeight(180)
        card.body().addWidget(self._user_table, 1)
        self.add_widget(card, 1)

        # Auth history table
        self.add_widget(SectionHeader(
            "Recent Authentication Decisions", "From authentication_history.",
            icon="🔐", accent=AI,
        ))
        acard = GlassCard("", AI)
        self._auth_table = QTableWidget(0, 4)
        self._auth_table.setHorizontalHeaderLabels(["Time", "Result", "Confidence", "Risk"])
        for c in range(4):
            self._auth_table.horizontalHeader().setSectionResizeMode(c, QHeaderView.Stretch)
        self._auth_table.verticalHeader().setVisible(False)
        self._auth_table.setShowGrid(False)
        self._auth_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._auth_table.setMinimumHeight(220)
        acard.body().addWidget(self._auth_table, 1)
        self.add_widget(acard, 1)

        self._empty = EmptyState(
            "🪪",
            "No identities enrolled",
            "No users have completed enrollment in this context.",
            "Complete the 7-day enrollment to create your behavioral identity.",
        )
        self._empty.setVisible(False)
        self.add_widget(self._empty)

    @staticmethod
    def _wrap(layout) -> QWidget:
        w = QWidget()
        w.setStyleSheet("background: transparent;")
        w.setLayout(layout)
        return w

    def refresh(self) -> None:
        if self._state.core is None:
            self._empty.setVisible(True)
            return
        counts = self._state.db_counts()
        model = self._state.model_info()
        enroll = self._state.enrollment()

        users = self._state.users()
        self._tile_users.set_value(str(len(users)) if users else str(counts.get("users", 0)))
        self._tile_users.set_sub(f"{counts.get('sessions', 0)} sessions")
        self._tile_enroll.set_value(enroll["status"].replace("_", " ").capitalize())
        self._tile_enroll.set_sub(f"day {enroll['current_day']}" if enroll["current_day"] else "not started")
        active = model.get("active")
        self._tile_model.set_value(f"v{active['version']}" if active else "—")
        self._tile_model.set_sub(active["model_id"][:10] if active else "no model deployed")
        self._tile_models.set_value(str(len(model.get("history", []))))
        self._tile_models.set_sub("model_versions table")

        # Users
        self._user_table.setRowCount(0)
        for u in users:
            self._user_table.insertRow(self._user_table.rowCount())
            i = self._user_table.rowCount() - 1
            self._user_table.setItem(i, 0, QTableWidgetItem(u.get("full_name") or u.get("user_id", "—")))
            self._user_table.setItem(i, 1, QTableWidgetItem(str(u.get("registration_date", ""))[:10]))
            es = u.get("enrollment_status", "not_started")
            item = QTableWidgetItem(es.replace("_", " ").capitalize())
            item.setForeground(QColor(severity_color(
                "success" if es == "completed" else "warning")))
            self._user_table.setItem(i, 2, item)
            self._user_table.setItem(i, 3, QTableWidgetItem(str(u.get("active_model_version") or "—")))
            st = u.get("account_status", "active")
            self._user_table.setItem(i, 4, QTableWidgetItem(st.capitalize()))

        # Auth history
        self._auth_table.setRowCount(0)
        for row in self._state.auth_history(40):
            self._auth_table.insertRow(self._auth_table.rowCount())
            i = self._auth_table.rowCount() - 1
            self._auth_table.setItem(i, 0, QTableWidgetItem(str(row.get("timestamp", ""))[11:19]))
            res = row.get("auth_result", "—")
            item = QTableWidgetItem(str(res).capitalize())
            item.setForeground(QColor(
                severity_color("success" if res == "authenticated" else "warning")))
            self._auth_table.setItem(i, 1, item)
            self._auth_table.setItem(i, 2, QTableWidgetItem(f"{float(row.get('confidence_score', 0)):.0%}"))
            risk = row.get("risk_level", "low")
            ritem = QTableWidgetItem(str(risk).upper())
            ritem.setForeground(QColor(severity_color(risk)))
            self._auth_table.setItem(i, 3, ritem)

        self._empty.setVisible(len(users) == 0)

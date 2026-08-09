"""Threat Hunting — search REAL collected behavioral features and events.

Queries run against the actual SQLite repository; results are real rows.
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
from src.ui.widgets import GlassCard, SearchInput, GlowButton, EmptyState, SectionHeader
from src.ui.pages.base import BasePage
from src.ui.state import SystemState


class ThreatHuntingPage(BasePage):
    """Hunt across real feature vectors stored by the engine."""

    TITLE = "Threat Hunting"
    ICON = "🔎"
    SUBTITLE = "Search real behavioral feature vectors in the local repository"

    def __init__(self, state: SystemState) -> None:
        super().__init__(state)

    def _build(self) -> None:
        toolbar = QHBoxLayout()
        toolbar.setSpacing(8)
        self._search = SearchInput("Search feature vectors by trust level, session, or vector…")
        self._search.returnPressed.connect(self._run)
        toolbar.addWidget(self._search, 1)
        run_btn = GlowButton("Hunt", icon="🔎", kind="solid")
        run_btn.clicked.connect(self._run)
        toolbar.addWidget(run_btn)
        w = QWidget()
        w.setStyleSheet("background: transparent;")
        w.setLayout(toolbar)
        self.add_widget(w)

        self._results_label = QLabel("Ready — enter a query to search the feature repository.")
        self._results_label.setStyleSheet(f"font-size: 12px; color: {TEXT_SEC}; background: transparent;")
        self.add_widget(self._results_label)

        card = GlassCard("FEATURE MATCHES", PRIMARY)
        self._table = QTableWidget(0, 4)
        self._table.setHorizontalHeaderLabels(["Time", "Session", "Trust", "Vector Preview"])
        for c in range(4):
            self._table.horizontalHeader().setSectionResizeMode(c, QHeaderView.Stretch)
        self._table.verticalHeader().setVisible(False)
        self._table.setShowGrid(False)
        self._table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._table.setMinimumHeight(320)
        card.body().addWidget(self._table, 1)
        self.add_widget(card, 1)

        self._empty = EmptyState(
            "🔎",
            "No feature data",
            "The feature repository is empty in this context.",
            "Feature vectors are written continuously by the behavioral pipeline while the application runs.",
        )
        self._empty.setVisible(False)
        self.add_widget(self._empty)

    def _run(self) -> None:
        query = self._search.text().strip().lower()
        repo = self._state._attr("feature_repo")
        if repo is None:
            self._results_label.setText("Feature repository not available.")
            return

        try:
            rows = repo.get_all_feature_vectors(limit=500)
        except Exception:
            rows = []

        if query:
            matches = []
            for r in rows:
                haystack = " ".join([
                    str(r.get("feature_id", "")),
                    str(r.get("timestamp", "")),
                    str(r.get("trust_level", "")),
                    str(r.get("session_id", "")),
                ]).lower()
                if query in haystack:
                    matches.append(r)
            rows = matches

        self._table.setRowCount(0)
        for r in rows:
            self._table.insertRow(self._table.rowCount())
            i = self._table.rowCount() - 1
            self._table.setItem(i, 0, QTableWidgetItem(str(r.get("timestamp", ""))[11:19]))
            self._table.setItem(i, 1, QTableWidgetItem(str(r.get("session_id", ""))[:16]))
            trust = r.get("trust_level", "medium")
            item = QTableWidgetItem(trust.capitalize())
            item.setForeground(QColor(severity_color(
                "success" if trust == "high" else "warning")))
            self._table.setItem(i, 2, item)
            vec = r.get("feature_vector", [])
            preview = "[" + ", ".join(f"{v:.2f}" for v in (vec[:12] if isinstance(vec, list) else [])) + (", …" if isinstance(vec, list) and len(vec) > 12 else "") + "]"
            self._table.setItem(i, 3, QTableWidgetItem(preview))

        self._results_label.setText(f"{len(rows)} matching feature vector(s).")
        self._empty.setVisible(len(rows) == 0 and not rows)

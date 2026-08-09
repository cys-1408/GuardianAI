"""Quarantine Center — honest empty state (feature not present in backend)."""

from __future__ import annotations

from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QFrame

from src.ui.theme import TEXT_PRI, TEXT_SEC, PRIMARY, WARNING
from src.ui.widgets import EmptyState, GlassCard, SectionHeader
from src.ui.pages.base import BasePage
from src.ui.state import SystemState


class QuarantinePage(BasePage):
    """Quarantine Center.

    The current GuardianAI backend has no quarantine subsystem, so this
    screen is an elegant empty state with guidance — never fake items.
    """

    TITLE = "Quarantine Center"
    ICON = "🧪"
    SUBTITLE = "Isolated threat containment"

    def _build(self) -> None:
        self.add_widget(SectionHeader(
            "Containment Vault",
            "Isolated storage for threats awaiting analyst review.",
            icon="🧪", accent=WARNING,
        ))

        self.add_widget(EmptyState(
            "🧪",
            "Quarantine vault is empty",
            "No threats are currently isolated. The quarantine subsystem will appear here "
            "once automated containment actions are wired into the backend.",
            "Contained items will surface here automatically — nothing is ever simulated.",
        ))

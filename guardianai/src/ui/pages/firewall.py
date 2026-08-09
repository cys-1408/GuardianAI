"""Firewall Events — honest empty state (no network firewall backend)."""

from __future__ import annotations

from PySide6.QtWidgets import QWidget

from src.ui.theme import PRIMARY, WARNING
from src.ui.widgets import EmptyState, SectionHeader
from src.ui.pages.base import BasePage
from src.ui.state import SystemState


class FirewallPage(BasePage):
    """Firewall Events.

    GuardianAI protects the endpoint behaviorally; it does not yet
    integrate with the Windows firewall, so this screen is an honest
    empty state with guidance.
    """

    TITLE = "Firewall Events"
    ICON = "🧱"
    SUBTITLE = "Network filtering activity"

    def _build(self) -> None:
        self.add_widget(SectionHeader(
            "Firewall Log Stream",
            "Connection filtering events from the local firewall.",
            icon="🧱", accent=WARNING,
        ))

        self.add_widget(EmptyState(
            "🧱",
            "No firewall integration",
            "GuardianAI does not currently read Windows firewall logs. Behavioral "
            "authentication protects this endpoint at the identity layer instead.",
            "A firewall connector can be added later — this screen will populate from "
            "the real Windows event log when it is configured.",
        ))

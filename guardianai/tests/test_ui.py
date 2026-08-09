"""Tests for the GuardianAI Command Center presentation layer."""

import pytest
from unittest.mock import MagicMock
from datetime import datetime

from PySide6.QtWidgets import QApplication, QLabel


@pytest.fixture(scope="session")
def qapp():
    """Create a QApplication for the entire test session."""
    app = QApplication.instance() or QApplication([])
    yield app


@pytest.fixture
def signals():
    """Reset the signals singleton so tests stay isolated."""
    import src.utils.signals as sig_mod
    sig_mod._signals_instance = None
    from src.utils.signals import get_signals
    yield get_signals()


class TestThemeAndWidgets:
    """Design system tokens and reusable widgets."""

    def test_theme_tokens(self, qapp):
        from src.ui.theme import BG, PANEL, CARD, PRIMARY, AI, SUCCESS, WARNING, CRITICAL, MUTED
        assert BG == "#05070B"
        assert PANEL == "#0E1117"
        assert CARD == "#151B23"
        assert PRIMARY == "#00D4FF"
        assert AI == "#7C4DFF"
        assert SUCCESS == "#00E676"
        assert WARNING == "#FFC107"
        assert CRITICAL == "#FF5252"
        assert MUTED == "#94A3B8"

    def test_app_stylesheet_generates(self, qapp):
        from src.ui.theme import app_stylesheet
        css = app_stylesheet()
        assert "QMainWindow" in css
        assert len(css) > 500

    def test_severity_color(self, qapp):
        from src.ui.theme import severity_color, CRITICAL, SUCCESS, PRIMARY
        assert severity_color("critical") == CRITICAL
        assert severity_color("low") == SUCCESS
        assert severity_color("unknown-thing") == PRIMARY

    def test_glass_card(self, qapp):
        from src.ui.widgets import GlassCard
        card = GlassCard("Title", accent="#00D4FF")
        assert card is not None
        card.set_title("New")

    def test_glow_button_variants(self, qapp):
        from src.ui.widgets import GlowButton
        for kind in ("solid", "outline", "ghost"):
            btn = GlowButton("Test", kind=kind)
            assert btn is not None

    def test_badge(self, qapp):
        from src.ui.widgets import Badge
        b = Badge("WARN", "warning")
        b.set_severity("critical")
        b.set_text("CRIT")
        assert b.text() == "CRIT"

    def test_sparkline(self, qapp):
        from src.ui.widgets import Sparkline
        s = Sparkline()
        s.set_data([0.1, 0.5, 0.9, 0.2])
        s.add_point(0.6)
        assert len(s._data) == 5

    def test_metric_tile(self, qapp):
        from src.ui.widgets import MetricTile
        t = MetricTile("Trust", value="50%")
        t.set_value("75%")
        t.set_sub("stable")
        assert "75%" in t._value.text()

    def test_empty_state(self, qapp):
        from src.ui.widgets import EmptyState
        es = EmptyState("icon", "Title", "Description", "Guidance")
        assert es is not None

    def test_search_input(self, qapp):
        from src.ui.widgets import SearchInput
        si = SearchInput("Find…")
        assert si.placeholderText() == "Find…"


class TestSystemState:
    """State provider must degrade gracefully without a core."""

    def test_state_without_core(self, qapp):
        from src.ui.state import SystemState
        state = SystemState(None)
        assert state.auth()["trust"] == 0.0
        assert state.auth()["auth_status"] == "unknown"
        assert state.db_counts() == {}
        assert state.agents() == []
        assert state.system_info()["app_name"] == "GuardianAI"

    def test_state_engine_stats(self, qapp):
        from src.ui.state import SystemState
        state = SystemState(None)
        assert state._engine_stats("confidence_engine") == {}


class TestDashboardPage:
    """Dashboard page renders with and without a core."""

    def test_widget_creation(self, qapp):
        from src.ui.state import SystemState
        from src.ui.pages.dashboard import DashboardPage
        page = DashboardPage(SystemState(None))
        assert page is not None

    def test_refresh_without_core(self, qapp):
        from src.ui.state import SystemState
        from src.ui.pages.dashboard import DashboardPage
        page = DashboardPage(SystemState(None))
        page.refresh()  # must not crash

    def test_refresh_with_mock_core(self, qapp):
        from src.ui.state import SystemState
        from src.ui.pages.dashboard import DashboardPage

        core = MagicMock()
        core.trust_mgr.get_stats.return_value = {"current_trust": 0.8, "trust_level": "high"}
        core.confidence_engine.get_stats.return_value = {
            "current_confidence": 0.9, "trend": "increasing", "min_conf": 0.1, "max_conf": 0.9}
        core.risk_engine.get_stats.return_value = {"current_risk_level": "low", "risk_score": 0.1}
        core.auth_mgr.current_status = "authenticated"
        core.db.get_table_info.return_value = {"sessions": 3, "users": 1}
        core.behavioral_repo.get_feature_count.return_value = 12
        core.behavioral_repo.get_trusted_count.return_value = 5

        page = DashboardPage(SystemState(core))
        page.refresh()
        assert page._tile_agents._value.text() != "—"


class TestMainWindow:
    """Main window shell, navigation, and lock gate."""

    def test_window_creation(self, qapp):
        from src.ui.main_window import MainWindow
        window = MainWindow()
        assert window is not None

    def test_page_count(self, qapp):
        from src.ui.main_window import MainWindow
        window = MainWindow()
        assert window._stack.count() == 19

    def test_navigate_to(self, qapp):
        from src.ui.main_window import MainWindow
        window = MainWindow()
        for key in ["dashboard", "live", "agents", "alerts", "settings",
                    "attack_graph", "network_map", "chat", "quarantine", "firewall"]:
            window.navigate_to(key)
            assert window._stack.currentWidget() is window._pages[key]
        window.navigate_to("bogus")  # must not crash
        assert window._stack.currentWidget() is window._pages["firewall"]

    def test_tray_icon(self, qapp):
        from src.ui.main_window import MainWindow
        window = MainWindow()
        assert window._tray is not None

    def test_auth_status_update(self, qapp):
        from src.ui.main_window import MainWindow
        window = MainWindow()
        signals = get_signals_instance()
        signals.auth_status_changed.emit("authenticated")

    def test_lock_screen_unlock(self, qapp):
        from src.ui.main_window import MainWindow
        window = MainWindow()
        assert window._lock is not None
        window._lock._authenticate()
        # unlock emits via single-shot timer
        from PySide6.QtCore import QEventLoop, QTimer
        loop = QEventLoop()
        QTimer.singleShot(800, loop.quit)
        loop.exec()
        assert window._lock.isHidden() is True


def get_signals_instance():
    from src.utils.signals import get_signals
    return get_signals()


class TestLiveMonitorPage:
    """Live monitor page."""

    def test_widget_creation(self, qapp):
        from src.ui.state import SystemState
        from src.ui.pages.live_monitor import LiveMonitorPage
        page = LiveMonitorPage(SystemState(None))
        assert page is not None

    def test_refresh(self, qapp):
        from src.ui.state import SystemState
        from src.ui.pages.live_monitor import LiveMonitorPage
        page = LiveMonitorPage(SystemState(None))
        page.refresh()


class TestAIAgentsPage:
    """AI agents page."""

    def test_widget_creation(self, qapp):
        from src.ui.state import SystemState
        from src.ui.pages.ai_agents import AIAgentsPage
        page = AIAgentsPage(SystemState(None))
        page.refresh()

    def test_agents_from_state(self, qapp):
        from src.ui.state import SystemState
        state = SystemState(None)
        assert state.agents() == []


class TestAlertsPage:
    """Alerts page."""

    def test_widget_creation(self, qapp):
        from src.ui.state import SystemState
        from src.ui.pages.alerts import AlertsPage
        page = AlertsPage(SystemState(None))
        page.refresh()


class TestEnrollmentWizard:
    """Enrollment wizard (re-themed, behavior preserved)."""

    def test_widget_creation(self, qapp):
        from src.ui.enrollment_wizard import EnrollmentWizardWidget
        widget = EnrollmentWizardWidget()
        assert widget is not None

    def test_day_selection(self, qapp):
        from src.ui.enrollment_wizard import EnrollmentWizardWidget
        widget = EnrollmentWizardWidget()
        widget._show_day(2)
        assert widget._current_day == 2

    def test_progress_bar_init(self, qapp):
        from src.ui.enrollment_wizard import EnrollmentWizardWidget
        widget = EnrollmentWizardWidget()
        assert widget._progress_bar.value() == 0

    def test_assignment_complete(self, qapp):
        from src.ui.enrollment_wizard import EnrollmentWizardWidget
        widget = EnrollmentWizardWidget()
        widget._on_day_completed(1, {"wpm": 30, "accuracy": 95.0})
        assert widget._progress_bar.value() == 14  # 1/7 ≈ 14%

    def test_progress_signal(self, qapp):
        from src.ui.enrollment_wizard import EnrollmentWizardWidget
        widget = EnrollmentWizardWidget()
        signals = get_signals_instance()
        signals.enrollment_progress.emit(0.5)
        assert widget._progress_bar.value() == 50

    def test_completed_signal(self, qapp):
        from src.ui.enrollment_wizard import EnrollmentWizardWidget
        widget = EnrollmentWizardWidget()
        signals = get_signals_instance()
        signals.enrollment_completed.emit()
        assert widget._progress_bar.value() == 100


class TestChatAssistant:
    """AI chat assistant grounded in real state."""

    def test_widget_creation(self, qapp):
        from src.ui.state import SystemState
        from src.ui.pages.chat import ChatAssistantPage
        page = ChatAssistantPage(SystemState(None))
        assert page is not None

    def test_answer_without_core(self, qapp):
        from src.ui.state import SystemState
        from src.ui.pages.chat import ChatAssistantPage
        page = ChatAssistantPage(SystemState(None))
        text, conf = page._answer("what is my trust score?")
        assert "not connected" in text
        assert conf < 0.5

    def test_answer_trust_with_mock_core(self, qapp):
        from src.ui.state import SystemState
        from src.ui.pages.chat import ChatAssistantPage

        core = MagicMock()
        core.trust_mgr.get_stats.return_value = {"current_trust": 0.85, "trust_level": "high"}
        core.confidence_engine.get_stats.return_value = {
            "current_confidence": 0.9, "trend": "increasing", "min_conf": 0.1, "max_conf": 0.9}
        core.risk_engine.get_stats.return_value = {"current_risk_level": "low", "risk_score": 0.1}
        core.auth_mgr.current_status = "authenticated"

        page = ChatAssistantPage(SystemState(core))
        text, conf = page._answer("how is my trust score?")
        assert "85%" in text
        assert conf >= 0.9

    def test_send_message(self, qapp):
        from src.ui.state import SystemState
        from src.ui.pages.chat import ChatAssistantPage
        page = ChatAssistantPage(SystemState(None))
        page._input.setPlainText("status?")
        page._send()
        assert page._thread.count() >= 3  # welcome + user + assistant


class TestOtherPages:
    """Remaining pages must construct and refresh safely."""

    @pytest.mark.parametrize("module,cls", [
        ("behavior_analytics", "BehaviorAnalyticsPage"),
        ("devices", "DevicesPage"),
        ("endpoints", "EndpointsPage"),
        ("identity", "IdentitySecurityPage"),
        ("audit_logs", "AuditLogsPage"),
        ("settings", "SettingsPage"),
        ("reports", "ReportsPage"),
        ("threat_intel", "ThreatIntelPage"),
        ("incident_response", "IncidentResponsePage"),
        ("threat_hunting", "ThreatHuntingPage"),
        ("quarantine", "QuarantinePage"),
        ("firewall", "FirewallPage"),
        ("attack_graph", "AttackGraphPage"),
        ("network_map", "NetworkMapPage"),
    ])
    def test_page_creation_and_refresh(self, qapp, module, cls):
        import importlib
        mod = importlib.import_module(f"src.ui.pages.{module}")
        page_cls = getattr(mod, cls)
        from src.ui.state import SystemState
        page = page_cls(SystemState(None))
        assert page is not None
        if hasattr(page, "refresh"):
            page.refresh()

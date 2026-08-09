"""Main Window — GuardianAI Security Command Center shell.

Layout:
  ┌────────────────────────────────────────────┐
  │ Top Security Command Bar                    │
  ├───────────┬────────────────────────────────┤
  │ Sidebar   │  Main Workspace (pages)         │
  │ (nav)     │                                 │
  ├───────────┴────────────────────────────────┤
  │ AI Status Footer                            │
  └────────────────────────────────────────────┘

The sidebar is a resizable panel (QSplitter). A session lock screen
overlays the workspace until the operator authenticates.
"""

from __future__ import annotations

import logging
from typing import Optional

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor, QIcon, QPixmap, QPainter, QFont
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QStackedWidget, QSystemTrayIcon, QMenu, QApplication,
    QSplitter, QGraphicsDropShadowEffect,
)

from src.utils.signals import get_signals
from src.utils.constants import APP_NAME, APP_VERSION
from src.ui.theme import (
    with_alpha,
    BG, PANEL, PRIMARY, AI, SUCCESS, WARNING, CRITICAL,
    MUTED, TEXT_PRI, TEXT_SEC, TEXT_DIM, BORDER, BORDER_STRONG,
    severity_color, app_stylesheet,
)
from src.ui.widgets import Dot, Badge
from src.ui.state import SystemState
from src.ui.lock_screen import LockScreen
from src.ui.pages.dashboard import DashboardPage
from src.ui.pages.live_monitor import LiveMonitorPage
from src.ui.pages.behavior_analytics import BehaviorAnalyticsPage
from src.ui.pages.ai_agents import AIAgentsPage
from src.ui.pages.alerts import AlertsPage
from src.ui.pages.devices import DevicesPage
from src.ui.pages.endpoints import EndpointsPage
from src.ui.pages.identity import IdentitySecurityPage
from src.ui.pages.audit_logs import AuditLogsPage
from src.ui.pages.settings import SettingsPage
from src.ui.pages.reports import ReportsPage
from src.ui.pages.threat_intel import ThreatIntelPage
from src.ui.pages.incident_response import IncidentResponsePage
from src.ui.pages.threat_hunting import ThreatHuntingPage
from src.ui.pages.quarantine import QuarantinePage
from src.ui.pages.firewall import FirewallPage
from src.ui.pages.attack_graph import AttackGraphPage
from src.ui.pages.network_map import NetworkMapPage
from src.ui.pages.chat import ChatAssistantPage

logger = logging.getLogger(__name__)


# ── Sidebar navigation definition ─────────────────────────────────────────
# (key, icon, label, accent) — accent is per-section for premium depth.

NAV_SECTIONS = [
    ("COMMAND", [
        ("dashboard",          "◈", "Dashboard",          PRIMARY),
    ]),
    ("DETECTION", [
        ("live",               "📡", "Live Threat Monitor", PRIMARY),
        ("behavior",           "🧬", "Behavior Analytics", AI),
        ("threat_intel",       "🛰", "Threat Intelligence", WARNING),
        ("firewall",           "🧱", "Firewall Events",    WARNING),
    ]),
    ("INTELLIGENCE", [
        ("agents",             "🤖", "AI Agents",          AI),
        ("attack_graph",       "🕸", "Attack Graph",       PRIMARY),
        ("network_map",        "🗺", "Network Map",        SUCCESS),
        ("chat",               "💬", "AI Assistant",       AI),
    ]),
    ("ASSETS", [
        ("devices",            "🖥", "Devices",            SUCCESS),
        ("endpoints",          "🔗", "Endpoints",          PRIMARY),
        ("identity",           "🪪", "Identity Security",  AI),
    ]),
    ("RESPONSE", [
        ("incidents",          "🚨", "Incident Response",  CRITICAL),
        ("hunting",            "🔎", "Threat Hunting",     WARNING),
        ("quarantine",         "🧪", "Quarantine Center",  WARNING),
        ("alerts",             "🔔", "Alerts",             CRITICAL),
    ]),
    ("OPERATIONS", [
        ("reports",            "📊", "Reports",            PRIMARY),
        ("audit",              "📜", "Audit Logs",         MUTED),
        ("settings",           "⚙️", "Settings",           MUTED),
    ]),
]

# key → (page class, title, icon, accent)
PAGE_MAP = {
    "dashboard":      (DashboardPage, "Security Command Dashboard", "◈", PRIMARY),
    "live":           (LiveMonitorPage, "Live Threat Monitor", "📡", PRIMARY),
    "behavior":       (BehaviorAnalyticsPage, "Behavior Analytics", "🧬", AI),
    "threat_intel":   (ThreatIntelPage, "Threat Intelligence", "🛰", WARNING),
    "firewall":       (FirewallPage, "Firewall Events", "🧱", WARNING),
    "agents":         (AIAgentsPage, "AI Agent Center", "🤖", AI),
    "attack_graph":   (AttackGraphPage, "Attack Graph", "🕸", PRIMARY),
    "network_map":    (NetworkMapPage, "Network Map", "🗺", SUCCESS),
    "chat":           (ChatAssistantPage, "AI Assistant", "💬", AI),
    "devices":        (DevicesPage, "Devices", "🖥", SUCCESS),
    "endpoints":      (EndpointsPage, "Endpoints", "🔗", PRIMARY),
    "identity":       (IdentitySecurityPage, "Identity Security", "🪪", AI),
    "incidents":      (IncidentResponsePage, "Incident Response", "🚨", CRITICAL),
    "hunting":        (ThreatHuntingPage, "Threat Hunting", "🔎", WARNING),
    "quarantine":     (QuarantinePage, "Quarantine Center", "🧪", WARNING),
    "alerts":         (AlertsPage, "Alert Center", "🔔", CRITICAL),
    "reports":        (ReportsPage, "Reports", "📊", PRIMARY),
    "audit":          (AuditLogsPage, "Audit Logs", "📜", MUTED),
    "settings":       (SettingsPage, "Settings", "⚙️", MUTED),
}


class NavButton(QFrame):
    """Sidebar navigation item with active glow + accent rule."""

    def __init__(self, key: str, icon: str, label: str, accent: str, shell) -> None:
        super().__init__()
        self.key = key
        self._shell = shell
        self._accent = accent
        self._active = False
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedHeight(40)

        lay = QHBoxLayout(self)
        lay.setContentsMargins(12, 0, 12, 0)
        lay.setSpacing(10)

        self._rule = QFrame()
        self._rule.setFixedSize(3, 20)
        self._rule.setStyleSheet(f"background: {accent}; border: none; border-radius: 2px;")
        self._rule.setVisible(False)
        lay.addWidget(self._rule)

        self._icon = QLabel(icon)
        self._icon.setFixedWidth(22)
        lay.addWidget(self._icon)

        self._label = QLabel(label)
        lay.addWidget(self._label, 1)

        self._update_style()

    def _update_style(self) -> None:
        if self._active:
            self.setStyleSheet(f"""
                QFrame {{
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 {with_alpha(self._accent, '26')}, stop:1 transparent);
                    border-radius: 9px;
                    margin: 1px 6px;
                }}
            """)
            self._label.setStyleSheet(
                f"font-size: 13px; font-weight: 600; color: {TEXT_PRI}; background: transparent;")
            self._icon.setStyleSheet(f"font-size: 14px; color: {self._accent}; background: transparent;")
            self._rule.setVisible(True)
        else:
            self.setStyleSheet("""
                QFrame { border-radius: 9px; margin: 1px 6px; }
                QFrame:hover { background: #0AFFFFFF; }
            """)
            self._label.setStyleSheet(f"font-size: 13px; color: {TEXT_SEC}; background: transparent;")
            self._icon.setStyleSheet(f"font-size: 14px; color: {TEXT_DIM}; background: transparent;")
            self._rule.setVisible(False)

    def set_active(self, active: bool) -> None:
        self._active = active
        self._update_style()
        if active:
            fx = QGraphicsDropShadowEffect()
            fx.setBlurRadius(16)
            fx.setOffset(0, 2)
            fx.setColor(QColor(with_alpha(self._accent, '40')))
            self.setGraphicsEffect(fx)
        else:
            self.setGraphicsEffect(None)

    def mousePressEvent(self, event) -> None:  # noqa: N802
        self._shell.navigate_to(self.key)
        super().mousePressEvent(event)


class Sidebar(QFrame):
    """Resizable glass navigation sidebar with grouped sections."""

    def __init__(self, shell) -> None:
        super().__init__()
        self._shell = shell
        self._buttons: dict[str, NavButton] = {}
        self.setMinimumWidth(190)
        self.setMaximumWidth(300)
        self.setStyleSheet(f"""
            QFrame {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {PANEL}, stop:1 #0B0E13);
                border-right: 1px solid {BORDER};
            }}
        """)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        # Brand header
        brand = QFrame()
        brand.setFixedHeight(68)
        brand.setStyleSheet(
            f"QFrame {{ background: #B2080A0E; border-bottom: 1px solid {BORDER}; }}")
        bl = QHBoxLayout(brand)
        bl.setContentsMargins(18, 0, 18, 0)
        bl.setSpacing(10)

        logo = QLabel("🛡")
        logo.setStyleSheet(f"font-size: 20px; background: transparent;")
        logo.setGraphicsEffect(self._glow(PRIMARY, 20, 60))
        bl.addWidget(logo)

        name_col = QVBoxLayout()
        name_col.setSpacing(0)
        name = QLabel(APP_NAME)
        name.setStyleSheet(
            f"font-size: 15px; font-weight: 800; color: {TEXT_PRI}; "
            f"background: transparent; letter-spacing: 1px;")
        name_col.addWidget(name)
        tag = QLabel("CYBER DEFENSE PLATFORM")
        tag.setStyleSheet(
            f"font-size: 8px; color: {TEXT_DIM}; background: transparent; "
            f"letter-spacing: 2px;")
        name_col.addWidget(tag)
        bl.addLayout(name_col)
        bl.addStretch()
        lay.addWidget(brand)

        # Nav scroll
        nav = QWidget()
        nav.setStyleSheet("background: transparent;")
        nav_lay = QVBoxLayout(nav)
        nav_lay.setContentsMargins(0, 8, 0, 8)
        nav_lay.setSpacing(2)

        for section, items in NAV_SECTIONS:
            sec = QLabel(section)
            sec.setContentsMargins(18, 10, 0, 4)
            sec.setStyleSheet(
                f"font-size: 9px; font-weight: 700; letter-spacing: 2px; "
                f"color: {TEXT_DIM}; background: transparent; padding-left: 12px;")
            nav_lay.addWidget(sec)
            for key, icon, label, accent in items:
                btn = NavButton(key, icon, label, accent, self._shell)
                self._buttons[key] = btn
                nav_lay.addWidget(btn)

        nav_lay.addStretch()
        lay.addWidget(nav, 1)

        # Footer status
        footer = QFrame()
        footer.setFixedHeight(52)
        footer.setStyleSheet(f"QFrame {{ border-top: 1px solid {BORDER}; background: transparent; }}")
        fl = QHBoxLayout(footer)
        fl.setContentsMargins(18, 0, 18, 0)
        ver = QLabel(f"v{APP_VERSION}")
        ver.setStyleSheet(f"font-size: 10px; color: {TEXT_DIM}; background: transparent;")
        fl.addWidget(ver)
        fl.addStretch()
        self._dot = Dot(SUCCESS, 8)
        fl.addWidget(self._dot)
        self._status_txt = QLabel("Active")
        self._status_txt.setStyleSheet(f"font-size: 10px; color: {SUCCESS}; background: transparent;")
        fl.addWidget(self._status_txt)
        lay.addWidget(footer)

    @staticmethod
    def _glow(color: str, radius: int, alpha: int) -> QGraphicsDropShadowEffect:
        fx = QGraphicsDropShadowEffect()
        fx.setBlurRadius(radius)
        fx.setOffset(0, 0)
        fx.setColor(QColor(color + f"{alpha:02X}"))
        return fx

    def set_active(self, key: str) -> None:
        for k, b in self._buttons.items():
            b.set_active(k == key)

    def set_status(self, status: str, color: Optional[str] = None) -> None:
        c = color or severity_color(status)
        self._dot.set_color(c)
        self._status_txt.setText(status.capitalize())
        self._status_txt.setStyleSheet(f"font-size: 10px; color: {c}; background: transparent;")


class TopCommandBar(QFrame):
    """Top security command bar: page title, status chips, system clock."""

    def __init__(self, shell) -> None:
        super().__init__()
        self._shell = shell
        self.setFixedHeight(56)
        self.setStyleSheet(f"""
            QFrame {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #0A0D12, stop:0.6 {PANEL}, stop:1 #0B0E13);
                border-bottom: 1px solid {BORDER};
            }}
        """)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(24, 0, 24, 0)
        lay.setSpacing(14)

        self._icon = QLabel("◈")
        self._icon.setStyleSheet(f"font-size: 16px; background: transparent; color: {PRIMARY};")
        lay.addWidget(self._icon)

        self._title = QLabel("Command Center")
        self._title.setStyleSheet(f"font-size: 15px; font-weight: 700; color: {TEXT_PRI}; background: transparent;")
        lay.addWidget(self._title)

        lay.addStretch()

        self._risk_badge = Badge("Risk: —", "info")
        lay.addWidget(self._risk_badge)
        self._model_badge = Badge("Model: —", "info")
        lay.addWidget(self._model_badge)
        self._auth_badge = Badge("Monitoring", "monitoring")
        lay.addWidget(self._auth_badge)

        sep = QFrame()
        sep.setFixedSize(1, 24)
        sep.setStyleSheet(f"background: {BORDER_STRONG}; border: none;")
        lay.addWidget(sep)

        self._clock = QLabel("--:--:--")
        self._clock.setStyleSheet(
            f"font-size: 13px; font-weight: 700; color: {TEXT_SEC}; background: transparent; "
            f"font-family: 'Consolas';")
        lay.addWidget(self._clock)

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(1000)
        self._tick()

    def _tick(self) -> None:
        from datetime import datetime
        self._clock.setText(datetime.now().strftime("%H:%M:%S"))

    def set_page(self, icon: str, title: str, accent: str) -> None:
        self._icon.setText(icon)
        self._icon.setStyleSheet(f"font-size: 16px; background: transparent; color: {accent};")
        self._title.setText(title)

    def set_auth_status(self, status: str) -> None:
        self._auth_badge.set_text(status.upper())
        self._auth_badge.set_severity(status)

    def set_risk(self, level: str, score: float) -> None:
        self._risk_badge.set_text(f"Risk: {level} · {score * 100:.0f}%")
        self._risk_badge.set_severity(level)

    def set_model(self, version: Optional[str]) -> None:
        self._model_badge.set_text(f"Model: v{version}" if version else "Model: —")


class AIStatusFooter(QFrame):
    """Bottom status bar: engine health, thread liveness, version."""

    def __init__(self) -> None:
        super().__init__()
        self.setFixedHeight(40)
        self.setStyleSheet(
            f"QFrame {{ background: #D9080A0E; border-top: 1px solid {BORDER}; }}")
        lay = QHBoxLayout(self)
        lay.setContentsMargins(20, 0, 20, 0)
        lay.setSpacing(14)

        self._items: dict[str, tuple[Dot, QLabel]] = {}
        for key, label in [
            ("collection", "Collection"),
            ("processing", "Processing"),
            ("auth", "Auth"),
            ("maintenance", "Maintenance"),
        ]:
            dot = Dot(SUCCESS, 8)
            lbl = QLabel(label)
            lbl.setStyleSheet(f"font-size: 10px; color: {TEXT_DIM}; background: transparent;")
            lay.addWidget(dot)
            lay.addWidget(lbl)
            self._items[key] = (dot, lbl)

        lay.addStretch()

        self._status = QLabel("●  System Ready")
        self._status.setStyleSheet(f"font-size: 11px; color: {SUCCESS}; background: transparent; font-weight: 600;")
        lay.addWidget(self._status)

        sep = QFrame()
        sep.setFixedSize(1, 18)
        sep.setStyleSheet(f"background: {BORDER_STRONG}; border: none;")
        lay.addWidget(sep)

        self._engine = QLabel(f"{APP_NAME} v{APP_VERSION}")
        self._engine.setStyleSheet(f"font-size: 10px; color: {TEXT_DIM}; background: transparent;")
        lay.addWidget(self._engine)

    def set_threads(self, health: list[dict]) -> None:
        for item in health:
            entry = self._items.get(item["key"])
            if entry:
                dot, _ = entry
                dot.set_color(SUCCESS if item["running"] else CRITICAL)

    def set_status(self, text: str, color: str = SUCCESS) -> None:
        self._status.setText(text)
        self._status.setStyleSheet(
            f"font-size: 11px; color: {color}; background: transparent; font-weight: 600;")


class MainWindow(QMainWindow):
    """GuardianAI Security Command Center — shown after enrollment completes."""

    def __init__(self, app_core=None) -> None:
        super().__init__()
        self._app_core = app_core
        self._state = SystemState(app_core)
        self._signals = get_signals()
        self._tray: Optional[QSystemTrayIcon] = None
        self._pages: dict[str, QWidget] = {}
        self._current_key = "dashboard"

        self._setup_ui()
        self._setup_tray()
        self._connect_signals()
        self.navigate_to("dashboard")
        self.showMaximized()

    # ── UI construction ──────────────────────────────────────────────
    def _setup_ui(self) -> None:
        self.setWindowTitle(f"{APP_NAME} — AI Cyber Defense Platform")
        self.setMinimumSize(1280, 820)
        self.setStyleSheet(app_stylesheet())

        central = QWidget()
        central.setObjectName("AppRoot")
        central.setStyleSheet(f"#AppRoot {{ background: {BG}; }}")
        self.setCentralWidget(central)

        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Top command bar
        self._top_bar = TopCommandBar(self)
        root.addWidget(self._top_bar)

        # Body: sidebar | workspace (resizable)
        self._splitter = QSplitter(Qt.Horizontal)
        self._splitter.setChildrenCollapsible(False)

        self._sidebar = Sidebar(self)
        self._splitter.addWidget(self._sidebar)

        workspace = QWidget()
        workspace.setStyleSheet("background: transparent;")
        ws_layout = QVBoxLayout(workspace)
        ws_layout.setContentsMargins(0, 0, 0, 0)
        ws_layout.setSpacing(0)

        self._stack = QStackedWidget()
        self._stack.setStyleSheet("background: transparent;")

        # Build all pages
        for key, (cls, title, icon, accent) in PAGE_MAP.items():
            page = cls(self._state)
            self._pages[key] = page
            self._stack.addWidget(page)

        ws_layout.addWidget(self._stack, 1)
        self._splitter.addWidget(workspace)

        self._splitter.setStretchFactor(0, 0)
        self._splitter.setStretchFactor(1, 1)
        self._splitter.setSizes([240, 1200])
        root.addWidget(self._splitter, 1)

        # AI status footer
        self._footer = AIStatusFooter()
        root.addWidget(self._footer)

        # Lock screen overlay
        self._lock = LockScreen(self._state)
        self._lock.unlocked.connect(self._on_unlocked)
        self._lock.setParent(central)
        self._lock.setGeometry(0, 0, self.width(), self.height())

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        if hasattr(self, "_lock"):
            self._lock.setGeometry(0, 0, self.width(), self.height())

    # ── Tray ─────────────────────────────────────────────────────────
    def _create_tray_icon(self) -> QIcon:
        px = QPixmap(32, 32)
        px.fill(Qt.transparent)
        p = QPainter(px)
        p.setRenderHint(QPainter.Antialiasing)
        p.setBrush(QColor(PRIMARY))
        p.setPen(Qt.NoPen)
        p.drawRoundedRect(2, 4, 28, 24, 6, 6)
        p.setBrush(QColor("#04121A"))
        p.setFont(QFont("Segoe UI", 13, QFont.Bold))
        p.drawText(px.rect(), Qt.AlignCenter, "G")
        p.end()
        return QIcon(px)

    def _setup_tray(self) -> None:
        self._tray = QSystemTrayIcon(self)
        self._tray.setIcon(self._create_tray_icon())
        self._tray.setToolTip(f"{APP_NAME} — AI Cyber Defense Platform")

        menu = QMenu()
        menu.addAction("◈  Open Command Center").triggered.connect(self.show_and_raise)
        menu.addSeparator()
        menu.addAction("✕  Exit").triggered.connect(self._quit)
        self._tray.setContextMenu(menu)
        self._tray.activated.connect(
            lambda r: self.show_and_raise()
            if r == QSystemTrayIcon.ActivationReason.DoubleClick else None
        )
        self._tray.show()

    # ── Signals ──────────────────────────────────────────────────────
    def _connect_signals(self) -> None:
        self._signals.auth_status_changed.connect(self._on_auth_status)
        self._signals.notification_received.connect(self._on_notification)

    # ── Navigation ───────────────────────────────────────────────────
    def navigate_to(self, key: str) -> None:
        if key not in self._pages:
            return
        self._current_key = key
        self._stack.setCurrentWidget(self._pages[key])
        self._sidebar.set_active(key)
        cls, title, icon, accent = PAGE_MAP[key]
        self._top_bar.set_page(icon, title, accent)
        page = self._pages[key]
        if hasattr(page, "refresh"):
            page.refresh()
        # Always refresh shell status (guards core=None internally)
        self._refresh_dashboard()

    # ── Slot handlers ────────────────────────────────────────────────
    def _refresh_dashboard(self) -> None:
        if self._state.core is None:
            return
        auth = self._state.auth()
        self._top_bar.set_auth_status(auth["auth_status"])
        self._top_bar.set_risk(auth["risk_level"], auth["risk_score"])
        model = self._state.model_info().get("active")
        self._top_bar.set_model(model.get("version") if model else None)
        self._sidebar.set_status(auth["auth_status"])
        self._footer.set_threads(self._state.thread_health())
        self._footer.set_status(f"●  {auth['auth_status'].capitalize()} · "
                                f"Trust {auth['trust'] * 100:.0f}%")

    def _on_auth_status(self, status: str) -> None:
        self._top_bar.set_auth_status(status)
        self._sidebar.set_status(status)
        self._footer.set_status(f"●  {status.capitalize()}",
                                severity_color(status))
        self._refresh_dashboard()

    def _on_unlocked(self) -> None:
        self._lock.hide()
        self._refresh_dashboard()

    def _on_notification(self, ntype: str, title: str, message: str) -> None:
        if self._tray:
            icon_map = {
                "info": QSystemTrayIcon.Information,
                "warning": QSystemTrayIcon.Warning,
                "error": QSystemTrayIcon.Critical,
                "success": QSystemTrayIcon.Information,
            }
            self._tray.showMessage(title, message,
                                   icon_map.get(ntype, QSystemTrayIcon.Information), 5000)

    # ── Window helpers ───────────────────────────────────────────────
    def show_and_raise(self) -> None:
        self.show()
        self.raise_()
        self.activateWindow()

    def _quit(self) -> None:
        if self._app_core:
            self._app_core.shutdown()
        QApplication.quit()

    def closeEvent(self, event) -> None:  # noqa: N802
        if self._tray and self._tray.isVisible():
            self.hide()
            event.ignore()
        else:
            if self._app_core:
                self._app_core.shutdown()
            event.accept()

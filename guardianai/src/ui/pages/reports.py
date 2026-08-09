"""Reports — generate real reports from live database and engine state."""

from __future__ import annotations

from datetime import datetime

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QPlainTextEdit,
)

from src.ui.theme import (
    PRIMARY, AI, SUCCESS, WARNING, CRITICAL, MUTED, TEXT_PRI, TEXT_SEC,
    TEXT_DIM, BORDER, severity_color, FONT_MONO,
)
from src.ui.widgets import GlassCard, GlowButton, EmptyState, SectionHeader
from src.ui.pages.base import BasePage
from src.ui.state import SystemState


class ReportsPage(BasePage):
    """Generate reports from the REAL database — never sample data."""

    TITLE = "Reports"
    ICON = "📊"
    SUBTITLE = "Generate operational reports from live application state"

    def __init__(self, state: SystemState) -> None:
        super().__init__(state)

    def _build(self) -> None:
        toolbar = QHBoxLayout()
        toolbar.setSpacing(8)
        b1 = GlowButton("Security Posture", icon="🛡")
        b1.clicked.connect(lambda: self._generate("posture"))
        toolbar.addWidget(b1)
        b2 = GlowButton("Session Summary", icon="💻")
        b2.clicked.connect(lambda: self._generate("sessions"))
        toolbar.addWidget(b2)
        b3 = GlowButton("Model & Training", icon="🧠")
        b3.clicked.connect(lambda: self._generate("model"))
        toolbar.addWidget(b3)
        b4 = GlowButton("Audit Digest", icon="📜")
        b4.clicked.connect(lambda: self._generate("audit"))
        toolbar.addWidget(b4)
        toolbar.addStretch()
        w = QWidget()
        w.setStyleSheet("background: transparent;")
        w.setLayout(toolbar)
        self.add_widget(w)

        card = GlassCard("REPORT OUTPUT", PRIMARY)
        self._report = QPlainTextEdit()
        self._report.setReadOnly(True)
        self._report.setFont(QFont(FONT_MONO, 10))
        self._report.setMinimumHeight(360)
        card.body().addWidget(self._report, 1)
        self.add_widget(card, 1)

    def _generate(self, kind: str) -> None:
        s = self._state
        counts = s.db_counts()
        auth = s.auth()
        model = s.model_info()
        lines = []

        lines.append("=" * 62)
        lines.append("  GUARDIANAI OPERATIONAL REPORT")
        lines.append(f"  Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("=" * 62)

        if kind == "posture":
            lines.append("\n[ SECURITY POSTURE ]")
            lines.append(f"  Auth status        : {auth['auth_status']}")
            lines.append(f"  Trust              : {auth['trust']:.0%} ({auth['trust_level']})")
            lines.append(f"  Confidence         : {auth['confidence']:.0%} ({auth['confidence_trend']})")
            lines.append(f"  Risk level         : {auth['risk_level'].upper()} ({auth['risk_score']:.0%})")
            lines.append(f"  Sessions           : {counts.get('sessions', 0)}")
            lines.append(f"  Users              : {counts.get('users', 0)}")
            lines.append(f"  Risk events        : {counts.get('risk_history', 0)}")
            lines.append(f"  Auth evaluations   : {counts.get('authentication_history', 0)}")
        elif kind == "sessions":
            lines.append("\n[ SESSION SUMMARY ]")
            stats = s.session_stats()
            lines.append(f"  Total sessions     : {stats.get('total_sessions', 0)}")
            lines.append(f"  Active sessions    : {stats.get('active_sessions', 0)}")
            dur = stats.get('total_duration_seconds', 0)
            lines.append(f"  Total duration     : {dur / 3600:.1f} hours")
            lines.append(f"\n  Recent sessions:")
            for sess in s.recent_sessions(8):
                lines.append(
                    f"    {sess.start_time.strftime('%m-%d %H:%M')}  "
                    f"{sess.user_id[:10]:10}  {sess.auth_status:14}  "
                    f"trust {sess.average_trust_score * 100:.0f}%")
        elif kind == "model":
            lines.append("\n[ MODEL & TRAINING ]")
            active = model.get("active")
            if active:
                lines.append(f"  Active model       : {active['model_id'][:12]}")
                lines.append(f"  Version            : v{active['version']}")
                lines.append(f"  Trained            : {active['training_date']}")
            else:
                lines.append("  Active model       : none deployed")
            lines.append(f"  Deployments        : {len(model.get('history', []))}")
            lines.append(f"  Stored features    : {counts.get('behavioral_features', 0)}")
            lines.append(f"  Trusted features   : {counts.get('trusted_features', 0)}")
            lines.append("\n  Training history:")
            for th in s.training_history(6):
                lines.append(
                    f"    {str(th.get('training_start', ''))[:16]}  "
                    f"v{th.get('model_version', '?')}  "
                    f"{th.get('duration_seconds', 0):.0f}s")
        else:
            lines.append("\n[ AUDIT DIGEST ]")
            events = s.audit_events(60)
            lines.append(f"  Recent events      : {len(events)}")
            lines.append(f"  Total audit rows   : {counts.get('audit_logs', 0)}")
            lines.append("\n  Latest events:")
            for e in events[:15]:
                lines.append(
                    f"    {str(e.get('timestamp', ''))[11:19]}  "
                    f"{str(e.get('severity', '')):12}  "
                    f"{str(e.get('component', ''))[:30]}")

        lines.append("\n" + "=" * 62)
        lines.append("  Report reflects real application data only.")
        lines.append("=" * 62)
        self._report.setPlainText("\n".join(lines))

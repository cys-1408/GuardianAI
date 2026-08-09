"""AI Chat Assistant — answers questions from REAL GuardianAI state.

The assistant is grounded: it queries the live system state provider
(trust, risk, sessions, models, audit trail) and streams a plain-text
answer with an estimated confidence. No canned marketing responses.
"""

from __future__ import annotations

import time
from datetime import datetime

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QTextEdit,
)

from src.ui.theme import (
    with_alpha,
    PRIMARY, AI, SUCCESS, WARNING, CRITICAL, MUTED, TEXT_PRI, TEXT_SEC,
    TEXT_DIM, BORDER, severity_color, FONT_MONO,
)
from src.ui.widgets import GlassCard, GlowButton, Badge, EmptyState
from src.ui.pages.base import BasePage
from src.ui.state import SystemState


class ChatBubble(QFrame):
    """A message bubble in the assistant thread."""

    def __init__(self, text: str, role: str, meta: str = "") -> None:
        super().__init__()
        is_user = role == "user"
        accent = AI if not is_user else PRIMARY
        self.setStyleSheet(f"""
            QFrame {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #F21A212B, stop:1 #FA10151D);
                border: 1px solid {with_alpha(accent, '33')};
                border-left: 3px solid {accent};
                border-radius: 12px;
            }}
        """)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(14, 10, 14, 10)
        lay.setSpacing(4)

        hdr = QHBoxLayout()
        who = QLabel("YOU" if is_user else "GUARDIAN AI")
        who.setStyleSheet(f"font-size: 10px; font-weight: 800; letter-spacing: 1px; color: {accent}; background: transparent;")
        hdr.addWidget(who)
        hdr.addStretch()
        if meta:
            m = QLabel(meta)
            m.setStyleSheet(f"font-size: 10px; color: {TEXT_DIM}; background: transparent; font-family: 'Consolas';")
            hdr.addWidget(m)
        lay.addLayout(hdr)

        body = QLabel(text)
        body.setWordWrap(True)
        body.setTextInteractionFlags(Qt.TextSelectableByMouse)
        body.setStyleSheet(f"font-size: 12px; color: {TEXT_PRI}; background: transparent;")
        lay.addWidget(body)


class ChatAssistantPage(BasePage):
    """Streaming AI assistant grounded in real system state."""

    TITLE = "AI Assistant"
    ICON = "💬"
    SUBTITLE = "Ask anything about your live security posture"

    def __init__(self, state: SystemState) -> None:
        super().__init__(state)
        self._history: list[dict] = []

    def _build(self) -> None:
        self.add_header_badge("Grounded · Real data only", "success")

        # Message thread
        self._thread = QVBoxLayout()
        self._thread.setSpacing(10)
        self._thread.addStretch()

        thread_wrap = QWidget()
        thread_wrap.setStyleSheet("background: transparent;")
        thread_wrap.setLayout(self._thread)
        self.add_widget(thread_wrap, 1)

        # Composer
        composer = GlassCard("", PRIMARY)
        cl = QHBoxLayout()
        cl.setSpacing(10)
        self._input = QTextEdit()
        self._input.setPlaceholderText(
            "Ask: what is my trust score? · summarize recent auth events · which model is active? …")
        self._input.setFixedHeight(64)
        cl.addWidget(self._input, 1)
        send_btn = GlowButton("Send", icon="➤", kind="solid")
        send_btn.clicked.connect(self._send)
        cl.addWidget(send_btn, 0, Qt.AlignBottom)
        composer.body().addLayout(cl)
        self.add_widget(composer)

        self._welcome()

    def _add_bubble(self, text: str, role: str, meta: str = "") -> None:
        b = ChatBubble(text, role, meta)
        self._thread.insertWidget(self._thread.count() - 1, b)
        # Keep thread bounded
        while self._thread.count() > 24:
            item = self._thread.takeAt(0)
            if item and item.widget():
                item.widget().deleteLater()

    def _welcome(self) -> None:
        self._add_bubble(
            "I'm Guardian AI — your live security analyst. I answer from the "
            "actual application state: trust & confidence engines, risk level, "
            "sessions, deployed models, and the audit trail.\n\n"
            "Try asking: \"How is my trust score?\", \"Summarize recent auth events\", "
            "or \"What model is deployed?\"",
            "assistant",
        )

    def _send(self) -> None:
        question = self._input.toPlainText().strip()
        if not question:
            return
        self._input.clear()
        self._add_bubble(question, "user")
        answer, confidence = self._answer(question)
        meta = f"conf {confidence * 100:.0f}% · {datetime.now().strftime('%H:%M:%S')}"
        self._add_bubble(answer, "assistant", meta)

    # ── Grounded answer engine ────────────────────────────────────
    def _answer(self, question: str) -> tuple[str, float]:
        q = question.lower()
        s = self._state
        auth = s.auth()

        if not s.core:
            return (
                "The application core is not connected in this context, so I "
                "can only report that no live state is available. Start the "
                "application and ask me again.", 0.2)

        if any(k in q for k in ("trust", "confidence", "how am i", "score")):
            return (
                f"Current behavioral trust is {auth['trust']:.0%} "
                f"(level: {auth['trust_level']}). Model confidence is "
                f"{auth['confidence']:.0%} with a {auth['confidence_trend']} trend. "
                f"Risk is {auth['risk_level']} (score {auth['risk_score'] * 100:.0f}%).", 0.95)

        if any(k in q for k in ("risk", "danger", "threat level")):
            return (
                f"Risk level: {auth['risk_level'].upper()} (score "
                f"{auth['risk_score'] * 100:.0f}%). This is computed live by the "
                f"adaptive risk engine from trust degradation and confidence "
                f"trend. Recent risk events: {s.db_counts().get('risk_history', 0)}.", 0.95)

        if any(k in q for k in ("auth", "session", "log", "event")):
            recent = s.auth_history(8)
            if not recent:
                return (
                    "No authentication decisions are recorded yet in this context. "
                    "Decisions accumulate while the application runs.", 0.6)
            lines = []
            for r in recent[:6]:
                lines.append(
                    f"  · {str(r.get('timestamp', ''))[11:19]} — "
                    f"{r.get('auth_result', '—')} (conf {float(r.get('confidence_score', 0)):.0%}, "
                    f"risk {r.get('risk_level', '—')})")
            return "Recent authentication decisions:\n" + "\n".join(lines), 0.9

        if any(k in q for k in ("model", "trained", "deployed", "version")):
            m = s.model_info()
            active = m.get("active")
            if active:
                return (
                    f"Active production model: v{active['version']} "
                    f"(trained {active['training_date']}). Total deployments: "
                    f"{len(m.get('history', []))}.", 0.95)
            return "No production model is deployed yet — it appears after enrollment completes.", 0.7

        if any(k in q for k in ("device", "endpoint", "host")):
            ep = s.endpoint()
            return (
                f"Protected endpoint: {ep['hostname']} ({ep['os']}). Agent: "
                f"{ep['agent']}. Trust {ep['trust'] * 100:.0f}%, risk {ep['risk']}. "
                f"Recorded sessions: {ep['sessions']}.", 0.9)

        if any(k in q for k in ("enroll", "onboard")):
            e = s.enrollment()
            return (
                f"Enrollment status: {e['status']} (current day {e['current_day']}). "
                f"Enrolled identities: {len(s.users())}.", 0.9)

        if any(k in q for k in ("agent", "subsystem", "thread", "health")):
            agents = s.agents()
            running = [a for a in agents if a["status"] == "running"]
            threads = s.thread_health()
            alive = [t["label"] for t in threads if t["running"]]
            return (
                f"{len(running)} of {len(agents)} autonomous agents running "
                f"({', '.join(a['name'] for a in running[:5])}…). Background "
                f"threads alive: {', '.join(alive) or 'none'}.", 0.9)

        if any(k in q for k in ("audit", "log", "record")):
            events = s.audit_events(10)
            if not events:
                return "The audit trail is empty in this context.", 0.6
            lines = [f"  · {e.get('timestamp', '')[:19]} [{e.get('severity', '')}] "
                     f"{e.get('component', '')}: {str(e.get('description', ''))[:60]}"
                     for e in events[:8]]
            return "Latest audit records:\n" + "\n".join(lines), 0.9

        if any(k in q for k in ("report", "summary", "posture")):
            counts = s.db_counts()
            return (
                f"Security posture summary:\n"
                f"  · Status: {auth['auth_status']} (trust {auth['trust']:.0%})\n"
                f"  · Sessions: {counts.get('sessions', 0)} · Users: {counts.get('users', 0)}\n"
                f"  · Risk events: {counts.get('risk_history', 0)}\n"
                f"  · Auth evaluations: {counts.get('authentication_history', 0)}\n"
                f"  · Feature vectors: {counts.get('behavioral_features', 0)}", 0.9)

        return (
            "I can answer about trust & confidence, risk level, authentication "
            "history, deployed models, endpoints, enrollment, agents, audit logs, "
            "and overall posture — all from live application state. Try one of "
            "those topics.", 0.4)

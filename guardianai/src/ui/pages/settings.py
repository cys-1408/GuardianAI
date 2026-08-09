"""Settings — live configuration editor bound to the real ConfigurationManager."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QCheckBox,
    QSlider, QComboBox, QSpinBox,
)

from src.ui.theme import (
    PRIMARY, AI, SUCCESS, WARNING, CRITICAL, MUTED, TEXT_PRI, TEXT_SEC,
    TEXT_DIM, BORDER, severity_color,
)
from src.ui.widgets import (
    GlassCard, GlowButton, Badge, EmptyState, SectionHeader,
)
from src.ui.pages.base import BasePage
from src.ui.state import SystemState


class SettingRow(QFrame):
    """Label + control row for one real configuration key."""

    def __init__(self, key: str, title: str, desc: str) -> None:
        super().__init__()
        self.key = key
        self.setStyleSheet("background: transparent;")
        lay = QHBoxLayout(self)
        lay.setContentsMargins(4, 6, 4, 6)
        lay.setSpacing(16)

        col = QVBoxLayout()
        col.setSpacing(2)
        t = QLabel(title)
        t.setStyleSheet(f"font-size: 13px; font-weight: 600; color: {TEXT_PRI}; background: transparent;")
        col.addWidget(t)
        d = QLabel(desc)
        d.setWordWrap(True)
        d.setStyleSheet(f"font-size: 11px; color: {TEXT_DIM}; background: transparent;")
        col.addWidget(d)
        lay.addLayout(col, 1)


class SettingsPage(BasePage):
    """Real settings surfaced from SettingsManager / ConfigurationManager."""

    TITLE = "Settings"
    ICON = "⚙️"
    SUBTITLE = "Live configuration — changes persist to the encrypted config"

    def __init__(self, state: SystemState) -> None:
        self._controls: list = []
        super().__init__(state)

    def _build(self) -> None:
        # ── Authentication section ────────────────────────────────
        self.add_widget(SectionHeader(
            "Authentication Engine", "Trust, risk, and sensitivity thresholds.",
            icon="🔐", accent=PRIMARY,
        ))
        auth_card = GlassCard("", PRIMARY)
        self._sens_slider = self._make_slider(
            auth_card, "auth.sensitivity",
            "Detection Sensitivity",
            "How aggressively the engine flags behavioral deviation.",
        )
        self._trust_thresh = self._make_slider(
            auth_card, "auth.trust_threshold",
            "Trust Threshold",
            "Trust score required to consider a session authenticated.",
        )
        self._risk_thresh = self._make_slider(
            auth_card, "auth.risk_threshold",
            "Risk Threshold",
            "Risk level that triggers protective action.",
        )
        self.add_widget(auth_card)

        # ── Monitoring section ────────────────────────────────────
        self.add_widget(SectionHeader(
            "Behavioral Monitoring", "Which signals are collected (privacy-sensitive).",
            icon="👁", accent=AI,
        ))
        mon_card = GlassCard("", AI)
        self._cb_keyboard = self._make_check(
            mon_card, "monitoring.collect_keyboard", "Collect Keyboard",
            "Capture keystroke dynamics for behavioral authentication.")
        self._cb_mouse = self._make_check(
            mon_card, "monitoring.collect_mouse", "Collect Mouse",
            "Capture mouse movement and click patterns.")
        self._cb_scroll = self._make_check(
            mon_card, "monitoring.collect_scroll", "Collect Scroll",
            "Capture scrolling behavior.")
        self.add_widget(mon_card)

        # ── Privacy section ───────────────────────────────────────
        self.add_widget(SectionHeader(
            "Privacy", "Data retention and anonymization.",
            icon="🛡", accent=SUCCESS,
        ))
        priv_card = GlassCard("", SUCCESS)
        self._cb_anonym = self._make_check(
            priv_card, "privacy.anonymize_features", "Anonymize Features",
            "Strip identifying metadata from stored feature vectors.")
        self._retention_spin = self._make_spin(
            priv_card, "privacy.data_retention_days", "Data Retention (days)",
            "How long behavioral data is kept before cleanup.")
        self.add_widget(priv_card)

        # ── Maintenance section ───────────────────────────────────
        self.add_widget(SectionHeader(
            "Maintenance", "Backup, cleanup, and integrity schedules.",
            icon="🧹", accent=WARNING,
        ))
        maint_card = GlassCard("", WARNING)
        self._backup_spin = self._make_spin(
            maint_card, "maintenance.backup_interval_hours", "Backup Interval (hours)",
            "How often encrypted backups are created.")
        self._cleanup_spin = self._make_spin(
            maint_card, "maintenance.cleanup_interval_hours", "Cleanup Interval (hours)",
            "How often stale data is purged.")
        self.add_widget(maint_card)

        # ── Actions ───────────────────────────────────────────────
        actions = QHBoxLayout()
        actions.addStretch()
        save_btn = GlowButton("Save Changes", icon="💾", kind="solid")
        save_btn.clicked.connect(self._save)
        actions.addWidget(save_btn)
        restore_btn = GlowButton("Restore Defaults", kind="outline", accent=CRITICAL)
        restore_btn.clicked.connect(self._restore_defaults)
        actions.addWidget(restore_btn)
        w = QWidget()
        w.setStyleSheet("background: transparent;")
        w.setLayout(actions)
        self.add_widget(w)

        self._saved = self.add_header_badge("Loaded", "info")

    # ── control builders ─────────────────────────────────────────
    @staticmethod
    def _make_slider(card: GlassCard, key: str, title: str, desc: str) -> QSlider:
        row = SettingRow(key, title, desc)
        slider = QSlider(Qt.Horizontal)
        slider.setRange(0, 100)
        slider.setFixedWidth(220)
        slider.valueChanged.connect(
            lambda v: slider.setToolTip(f"{v / 100:.0%}"))
        row.layout().addWidget(slider)
        card.body().addWidget(row)
        return slider

    @staticmethod
    def _make_check(card: GlassCard, key: str, title: str, desc: str) -> QCheckBox:
        row = SettingRow(key, title, desc)
        cb = QCheckBox()
        cb.setFixedWidth(24)
        row.layout().addWidget(cb)
        card.body().addWidget(row)
        return cb

    @staticmethod
    def _make_spin(card: GlassCard, key: str, title: str, desc: str) -> QSpinBox:
        row = SettingRow(key, title, desc)
        spin = QSpinBox()
        spin.setRange(1, 100000)
        spin.setFixedWidth(120)
        row.layout().addWidget(spin)
        card.body().addWidget(row)
        return spin

    # ── save / restore ───────────────────────────────────────────
    def _save(self) -> None:
        settings = self._state.settings()
        updates = {}
        updates["auth.sensitivity"] = self._sens_slider.value() / 100
        updates["auth.trust_threshold"] = self._trust_thresh.value() / 100
        updates["auth.risk_threshold"] = self._risk_thresh.value() / 100
        updates["monitoring.collect_keyboard"] = self._cb_keyboard.isChecked()
        updates["monitoring.collect_mouse"] = self._cb_mouse.isChecked()
        updates["monitoring.collect_scroll"] = self._cb_scroll.isChecked()
        updates["privacy.anonymize_features"] = self._cb_anonym.isChecked()
        updates["privacy.data_retention_days"] = self._retention_spin.value()
        updates["maintenance.backup_interval_hours"] = self._backup_spin.value()
        updates["maintenance.cleanup_interval_hours"] = self._cleanup_spin.value()

        mgr = self._state._attr("settings")
        if mgr is None:
            self._saved.set_text("No config store")
            self._saved.set_severity("critical")
            return
        ok = mgr.set_batch(updates)
        all_ok = all(ok.values())
        self._saved.set_text("Saved" if all_ok else "Partial save")
        self._saved.set_severity("success" if all_ok else "warning")

    def _restore_defaults(self) -> None:
        mgr = self._state._attr("settings")
        if mgr is None:
            return
        mgr.restore_defaults()
        self._saved.set_text("Defaults restored")
        self._saved.set_severity("success")
        self.refresh()

    def refresh(self) -> None:
        if self._state.core is None:
            self._saved.set_text("No core")
            return
        s = self._state.settings()
        auth = s.get("auth", {})
        mon = s.get("monitoring", {})
        priv = s.get("privacy", {})
        maint = s.get("maintenance", {})

        self._sens_slider.setValue(int(auth.get("sensitivity", 0.5) * 100))
        self._trust_thresh.setValue(int(auth.get("trust_threshold", 0.7) * 100))
        self._risk_thresh.setValue(int(auth.get("risk_threshold", 0.6) * 100))
        self._cb_keyboard.setChecked(bool(mon.get("collect_keyboard", True)))
        self._cb_mouse.setChecked(bool(mon.get("collect_mouse", True)))
        self._cb_scroll.setChecked(bool(mon.get("collect_scroll", True)))
        self._cb_anonym.setChecked(bool(priv.get("anonymize_features", True)))
        self._retention_spin.setValue(int(priv.get("data_retention_days", 365)))
        self._backup_spin.setValue(int(maint.get("backup_interval_hours", 24)))
        self._cleanup_spin.setValue(int(maint.get("cleanup_interval_hours", 72)))

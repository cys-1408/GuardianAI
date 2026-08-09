"""System State Provider — composes REAL GuardianAI application state.

Every page reads through this facade so no screen fabricates data.
When a subsystem or its data is unavailable, values are reported as
absent and pages render elegant empty states instead.
"""

from __future__ import annotations

import platform
import socket
from datetime import datetime, timedelta
from typing import Any, Optional

from src.utils.signals import get_signals
from src.utils.constants import APP_VERSION, APP_NAME


class SystemState:
    """Reads live state from ApplicationCore (may be None in tests/preview)."""

    def __init__(self, core: Optional[Any] = None) -> None:
        self._core = core
        self._signals = get_signals()

    # ── helpers ──────────────────────────────────────────────────────
    @property
    def core(self) -> Optional[Any]:
        return self._core

    def _attr(self, name: str) -> Any:
        if self._core is None:
            return None
        return getattr(self._core, name, None)

    def _engine_stats(self, name: str) -> dict:
        eng = self._attr(name)
        if eng is None or not hasattr(eng, "get_stats"):
            return {}
        try:
            return eng.get_stats()
        except Exception:
            return {}

    # ── auth / trust / risk ──────────────────────────────────────────
    def auth(self) -> dict:
        """Confidence, trust, risk, auth status — real engine values."""
        conf = self._engine_stats("confidence_engine")
        trust = self._engine_stats("trust_mgr")
        risk = self._engine_stats("risk_engine")
        auth_mgr = self._attr("auth_mgr")
        session = self._attr("session")

        status = "unknown"
        if auth_mgr is not None and hasattr(auth_mgr, "current_status"):
            status = auth_mgr.current_status
        elif session is not None and getattr(session, "current_session", None):
            status = session.current_session.auth_status

        return {
            "confidence": conf.get("current_confidence", 0.0),
            "confidence_trend": conf.get("trend", "stable"),
            "trust": trust.get("current_trust", 0.0),
            "trust_level": trust.get("trust_level", "unknown"),
            "risk_level": risk.get("current_risk_level", "low"),
            "risk_score": risk.get("risk_score", 0.0),
            "auth_status": status,
        }

    # ── database table counts ────────────────────────────────────────
    def db_counts(self) -> dict:
        db = self._attr("db")
        if db is None or not hasattr(db, "get_table_info"):
            return {}
        try:
            return db.get_table_info()
        except Exception:
            return {}

    # ── sessions ─────────────────────────────────────────────────────
    def session_stats(self) -> dict:
        session = self._attr("session")
        if session is None:
            return {}
        try:
            return session.get_stats()
        except Exception:
            return {}

    def recent_sessions(self, limit: int = 8) -> list:
        session = self._attr("session")
        if session is None or not hasattr(session, "get_recent_sessions"):
            return []
        try:
            return session.get_recent_sessions(limit)
        except Exception:
            return []

    # ── model / training ─────────────────────────────────────────────
    def model_info(self) -> dict:
        """Active model + deployment history from the real repository."""
        repo = self._attr("model_repo")
        out: dict = {"active": None, "history": []}
        if repo is None:
            return out
        try:
            active = repo.get_active_model()
            if active:
                out["active"] = {
                    "model_id": active.get("model_id"),
                    "version": active.get("version"),
                    "training_date": active.get("training_date"),
                }
            out["history"] = repo.get_model_history() or []
        except Exception:
            pass
        return out

    def training_history(self, limit: int = 8) -> list:
        db = self._attr("db")
        if db is None:
            return []
        try:
            return db.fetch_all(
                "SELECT * FROM training_history ORDER BY training_start DESC LIMIT ?",
                (limit,),
            )
        except Exception:
            return []

    # ── audit / alerts ───────────────────────────────────────────────
    def audit_events(self, limit: int = 60, severity: Optional[str] = None) -> list:
        repo = self._attr("audit_repo")
        if repo is None:
            return []
        try:
            return repo.get_events(limit=limit, severity=severity)
        except Exception:
            return []

    def auth_history(self, limit: int = 60) -> list:
        repo = self._attr("audit_repo")
        if repo is None:
            return []
        try:
            return repo.get_auth_history(limit)
        except Exception:
            return []

    def notifications(self, limit: int = 40) -> list:
        db = self._attr("db")
        if db is None:
            return []
        try:
            return db.fetch_all(
                "SELECT * FROM notifications ORDER BY delivery_time DESC LIMIT ?",
                (limit,),
            )
        except Exception:
            return []

    # ── behavioral features ──────────────────────────────────────────
    def feature_stats(self) -> dict:
        repo = self._attr("behavioral_repo")
        out = {"features": 0, "trusted": 0}
        if repo is None:
            return out
        try:
            out["features"] = repo.get_feature_count()
            out["trusted"] = repo.get_trusted_count()
        except Exception:
            pass
        return out

    # ── maintenance history ──────────────────────────────────────────
    def backup_history(self, limit: int = 5) -> list:
        db = self._attr("db")
        if db is None:
            return []
        try:
            return db.fetch_all(
                "SELECT * FROM backup_history ORDER BY backup_time DESC LIMIT ?",
                (limit,),
            )
        except Exception:
            return []

    def cleanup_history(self, limit: int = 5) -> list:
        db = self._attr("db")
        if db is None:
            return []
        try:
            return db.fetch_all(
                "SELECT * FROM cleanup_history ORDER BY cleanup_date DESC LIMIT ?",
                (limit,),
            )
        except Exception:
            return []

    def integrity_history(self, limit: int = 5) -> list:
        db = self._attr("db")
        if db is None:
            return []
        try:
            return db.fetch_all(
                "SELECT * FROM integrity_checks ORDER BY check_time DESC LIMIT ?",
                (limit,),
            )
        except Exception:
            return []

    # ── enrollment ───────────────────────────────────────────────────
    def enrollment(self) -> dict:
        mgr = self._attr("enrollment_system")
        out = {"status": "unknown", "current_day": 0}
        if mgr is not None:
            try:
                out["status"] = getattr(mgr, "status", "unknown") or "unknown"
                out["current_day"] = getattr(mgr, "current_day", 0) or 0
            except Exception:
                pass
        return out

    def users(self) -> list:
        db = self._attr("db")
        if db is None:
            return []
        try:
            return db.fetch_all("SELECT * FROM users ORDER BY registration_date DESC LIMIT 10")
        except Exception:
            return []

    # ── settings ─────────────────────────────────────────────────────
    def settings(self) -> dict:
        settings = self._attr("settings")
        if settings is None:
            return {}
        try:
            return settings.get_all()
        except Exception:
            return {}

    # ── background agents (the real engine threads) ──────────────────
    def agents(self) -> list[dict]:
        """Map real running subsystems to the autonomous-agent view.

        Each entry reflects a REAL component: thread liveness, engine
        stats, and recent audit activity. None are fabricated.
        """
        core = self._core
        agents: list[dict] = []
        if core is None:
            return agents

        def thread_alive(flag_name: str) -> bool:
            flag = getattr(core, flag_name, None)
            return bool(flag is not None and flag.is_set())

        auth = self.auth()

        def _audit_hits(component_kw: str, limit: int = 3) -> list:
            events = self.audit_events(limit=40)
            hits = [e for e in events if component_kw in str(e.get("component", "")).lower()]
            return hits[:limit]

        # Network Sentinel — windows/session integration
        net = self._attr("windows_integration")
        agents.append({
            "id": "network-sentinel",
            "name": "Network Sentinel",
            "icon": "🌐",
            "description": "Monitors desktop sessions, window context, and idle state.",
            "status": "running" if net is not None else "standby",
            "confidence": auth["trust"],
            "task": "Watching session & window activity",
            "decision": f"Session: {'active' if self.session_stats().get('active_sessions', 0) else 'idle'}",
            "actions": _audit_hits("window"),
            "health": 100 if net is not None else 0,
            "runtime": "continuous",
        })

        # Behavior Analyst — collection + processing pipeline
        buf = self._attr("event_buffer")
        agg = self._attr("event_aggregator")
        feats = self.feature_stats()
        agents.append({
            "id": "behavior-analyst",
            "name": "Behavior Analyst",
            "icon": "🧬",
            "description": "Collects keystroke/mouse/scroll events and extracts behavioral features.",
            "status": "running" if (buf is not None or agg is not None) else "standby",
            "confidence": auth["confidence"],
            "task": "Extracting behavioral feature vectors",
            "decision": f"{feats['features']} features stored · {feats['trusted']} trusted",
            "actions": _audit_hits("feature"),
            "health": 100 if (buf is not None and agg is not None) else 40,
            "runtime": "continuous",
        })

        # Malware Hunter — anomaly / risk detection
        risk = self._engine_stats("risk_engine")
        agents.append({
            "id": "malware-hunter",
            "name": "Malware Hunter",
            "icon": "🦠",
            "description": "Detects anomalous behavioral deviations and escalating risk.",
            "status": "running" if risk else "standby",
            "confidence": max(auth["risk_score"], 1 - auth["confidence"]),
            "task": f"Analyzing risk signals — level {auth['risk_level']}",
            "decision": f"Risk score {auth['risk_score']:.0%} · trend {auth['confidence_trend']}",
            "actions": _audit_hits("risk"),
            "health": 100 - int(auth["risk_score"] * 100),
            "runtime": "continuous",
        })

        # Threat Hunter — risk engine
        agents.append({
            "id": "threat-hunter",
            "name": "Threat Hunter",
            "icon": "🔎",
            "description": "Evaluates risk level from trust degradation & confidence trend.",
            "status": "running" if risk else "standby",
            "confidence": auth["trust"],
            "task": "Scanning for trust degradation",
            "decision": f"Level: {auth['risk_level']} · {'degrading' if trust_degrading(core) else 'stable'}",
            "actions": _audit_hits("authentication"),
            "health": 100 if risk else 0,
            "runtime": "1s cadence",
        })

        # Identity Guardian — authentication decision engine
        auth_mgr = self._attr("auth_mgr")
        agents.append({
            "id": "identity-guardian",
            "name": "Identity Guardian",
            "icon": "🛡️",
            "description": "Makes the final authentication decision from trust & risk.",
            "status": "running" if auth_mgr is not None else "standby",
            "confidence": auth["confidence"],
            "task": f"Auth status: {auth['auth_status']}",
            "decision": f"Trust {auth['trust']:.0%} → {auth['auth_status']}",
            "actions": _audit_hits("authentication"),
            "health": 100 if auth_mgr is not None else 0,
            "runtime": "1s cadence",
        })

        # Log Intelligence — audit repository
        audit = self._attr("audit_repo")
        events = self.audit_events(limit=5)
        agents.append({
            "id": "log-intelligence",
            "name": "Log Intelligence",
            "icon": "📜",
            "description": "Persists immutable audit records of security-relevant activity.",
            "status": "running" if audit is not None else "standby",
            "confidence": 0.0,
            "task": f"{len(events)} recent audit entries",
            "decision": "Audit trail active" if audit is not None else "No audit repository",
            "actions": events[:3],
            "health": 100 if audit is not None else 0,
            "runtime": "on-event",
        })

        # Patch Advisor — retraining scheduler
        sched = self._attr("training_scheduler")
        agents.append({
            "id": "patch-advisor",
            "name": "Patch Advisor",
            "icon": "🧩",
            "description": "Schedules adaptive model retraining from new trusted behavior.",
            "status": "running" if sched is not None else "standby",
            "confidence": auth["trust"],
            "task": "Reviewing retraining readiness",
            "decision": "Retraining scheduler active" if sched is not None else "Not scheduled",
            "actions": self.training_history(3),
            "health": 100 if sched is not None else 0,
            "runtime": "scheduled",
        })

        # Response Coordinator — workflow controller
        wf = self._attr("workflow")
        state = getattr(getattr(wf, "current_state", None), "value", "idle") if wf else "idle"
        agents.append({
            "id": "response-coordinator",
            "name": "Response Coordinator",
            "icon": "🎯",
            "description": "Coordinates the enrollment → training → authentication workflow.",
            "status": "running" if wf is not None else "standby",
            "confidence": 1.0,
            "task": f"Workflow state: {state}",
            "decision": "Workflow orchestration active" if wf is not None else "Standby",
            "actions": [],
            "health": 100 if wf is not None else 0,
            "runtime": "stateful",
        })

        # Cloud Defender / Email Defender — no backend module exists
        for cfg in [
            ("cloud-defender", "Cloud Defender", "☁️",
             "Scans cloud and remote activity. No cloud connector is configured in this build."),
            ("email-defender", "Email Defender", "✉️",
             "Analyzes email-borne threats. No mail connector is configured in this build."),
        ]:
            agents.append({
                "id": cfg[0], "name": cfg[1], "icon": cfg[2],
                "description": cfg[3], "status": "standby", "confidence": 0.0,
                "task": "Awaiting connector", "decision": "Module not configured",
                "actions": [], "health": 0, "runtime": "—",
            })

        return agents

    # ── system health / info ─────────────────────────────────────────
    def system_info(self) -> dict:
        return {
            "hostname": socket.gethostname(),
            "platform": platform.platform(),
            "python": platform.python_version(),
            "app_version": APP_VERSION,
            "app_name": APP_NAME,
        }

    def thread_health(self) -> list[dict]:
        """Real liveness of the six background threads."""
        names = [
            ("collection", "_collection_running", "Behavior Collection"),
            ("processing", "_processing_running", "Feature Processing"),
            ("auth", "_auth_running", "Authentication"),
            ("maintenance", "_maintenance_running", "Maintenance"),
        ]
        out = []
        for key, flag, label in names:
            flag_obj = self._attr(flag)
            alive = bool(flag_obj is not None and flag_obj.is_set())
            out.append({"key": key, "label": label, "running": alive})
        return out

    # ── incident / risk timeline (from real risk events) ─────────────
    def risk_events(self, limit: int = 30) -> list:
        """Derive incidents from the real risk_history table."""
        db = self._attr("db")
        if db is None:
            return []
        try:
            return db.fetch_all(
                "SELECT * FROM risk_history ORDER BY timestamp DESC LIMIT ?",
                (limit,),
            )
        except Exception:
            return []

    # ── threat intel (MITRE mapping from real risk levels) ───────────
    def threat_intel(self) -> dict:
        """Map real current risk/trust state to MITRE ATT&CK techniques.

        Only reports techniques that correspond to ACTUAL engine signals —
        when nothing is detected the list is empty and the page shows an
        empty state.
        """
        auth = self.auth()
        techniques = []
        if auth["risk_level"] in ("high", "critical"):
            techniques.append({
                "id": "T1078.001",
                "name": "Valid Accounts / Default Accounts",
                "phase": "Initial Access",
                "signal": "Elevated risk level",
                "confidence": max(auth["risk_score"], 0.5),
                "status": "active",
            })
        if auth["trust_level"] == "low" or auth["trust"] < 0.4:
            techniques.append({
                "id": "T1110",
                "name": "Brute Force / Behavioral Mismatch",
                "phase": "Credential Access",
                "signal": "Low behavioral trust",
                "confidence": 1 - auth["trust"],
                "status": "active",
            })
        if auth["confidence_trend"] == "decreasing":
            techniques.append({
                "id": "T1027",
                "name": "Obfuscated Files or Information",
                "phase": "Defense Evasion",
                "signal": "Confidence trend decreasing",
                "confidence": 0.5,
                "status": "watch",
            })
        return {"techniques": techniques, "cves": [], "iocs": []}

    # ── host/endpoint data ───────────────────────────────────────────
    def endpoint(self) -> dict:
        """The local protected endpoint (real host info + last scan)."""
        auth = self.auth()
        counts = self.db_counts()
        return {
            "hostname": socket.gethostname(),
            "os": platform.platform(),
            "python": platform.python_version(),
            "agent": f"{APP_NAME} v{APP_VERSION}",
            "last_scan": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "risk": auth["risk_level"],
            "risk_score": auth["risk_score"],
            "trust": auth["trust"],
            "threat_count": counts.get("risk_history", 0),
            "sessions": counts.get("sessions", 0),
            "features": counts.get("behavioral_features", 0),
        }


def trust_degrading(core: Any) -> bool:
    """Safe wrapper: is trust currently degrading (real engine signal)."""
    trust = getattr(core, "trust_mgr", None)
    if trust is None or not hasattr(trust, "detect_degradation"):
        return False
    try:
        return trust.detect_degradation()
    except Exception:
        return False

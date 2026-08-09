"""Authentication Manager - Makes final authentication decisions based on trust and risk."""

import logging
from datetime import datetime
from typing import Any, Optional

from src.utils.signals import get_signals, AuthDecision
from src.utils.constants import AuthStatus, RiskLevel
from src.ai.trust import TrustScoreManager
from src.ai.risk import AdaptiveRiskEngine
from src.ai.confidence import ConfidenceEngine
from src.application.session import SessionManager

logger = logging.getLogger(__name__)


class AuthenticationManager:
    """Makes final authentication decisions based on trust and risk assessment."""

    def __init__(self, trust_mgr: TrustScoreManager, risk_engine: 'AdaptiveRiskEngine',
                 confidence_engine: ConfidenceEngine,
                 session_mgr: SessionManager) -> None:
        self._trust = trust_mgr
        self._risk = risk_engine
        self._confidence = confidence_engine
        self._session = session_mgr
        self._signals = get_signals()
        self._current_status: str = AuthStatus.MONITORING.value
        self._consecutive_low = 0

    def evaluate(self) -> AuthDecision:
        """Evaluate current authentication state and make a decision.

        Returns:
            Authentication decision
        """
        confidence = self._confidence.current_confidence
        trust = self._trust.current_trust
        risk_level = self._risk.current_risk_level
        session_id = self._session.current_session_id

        # Determine authentication status
        if risk_level == RiskLevel.CRITICAL.value:
            status = AuthStatus.LOCKED.value
            self._consecutive_low += 1
        elif risk_level == RiskLevel.HIGH.value:
            status = AuthStatus.DEGRADED.value
            self._consecutive_low += 1
        elif trust < 0.3:
            status = AuthStatus.DEGRADED.value
            self._consecutive_low += 1
        elif trust >= 0.7:
            status = AuthStatus.AUTHENTICATED.value
            self._consecutive_low = 0
        else:
            status = AuthStatus.MONITORING.value
            self._consecutive_low = 0

        self._current_status = status
        self._session.update_auth_status(status, session_id)

        decision = AuthDecision(
            status=status,
            confidence=confidence,
            trust_score=trust,
            risk_level=risk_level,
            timestamp=datetime.now(),
            session_id=session_id,
            details={
                "consecutive_low": self._consecutive_low,
                "trust_level": self._trust.get_trust_level().value,
                "confidence_trend": self._confidence.get_trend(),
            },
        )

        self._signals.auth_decision.emit(decision)
        self._signals.auth_status_changed.emit(status)
        return decision

    @property
    def current_status(self) -> str:
        return self._current_status

"""Tests for SessionManager."""

import pytest
from datetime import datetime
from src.application.session import SessionManager


class TestSessionManager:
    def test_create_session(self):
        sm = SessionManager()
        sm.set_user("test_user")
        sid = sm.create_session()
        assert sid is not None
        assert sm.current_session_id == sid

    def test_session_properties(self):
        sm = SessionManager()
        sm.set_user("test_user")
        sid = sm.create_session()
        session = sm.current_session
        assert session is not None
        assert session.user_id == "test_user"
        assert session.is_active == True
        assert session.auth_status == "monitoring"

    def test_close_session(self):
        sm = SessionManager()
        sm.set_user("test_user")
        sid = sm.create_session()
        sm.close_session(sid)
        session = sm.get_session(sid)
        assert session is not None
        assert session.is_active == False
        assert session.end_time is not None

    def test_record_activity(self):
        sm = SessionManager()
        sm.set_user("test_user")
        sm.create_session()
        sm.record_activity()
        session = sm.current_session
        assert session.event_count == 1

    def test_update_trust_score(self):
        sm = SessionManager()
        sm.set_user("test_user")
        sm.create_session()
        sm.update_trust_score(0.85)
        session = sm.current_session
        assert session.average_trust_score == 0.85

    def test_update_auth_status(self):
        sm = SessionManager()
        sm.set_user("test_user")
        sm.create_session()
        sm.update_auth_status("authenticated")
        session = sm.current_session
        assert session.auth_status == "authenticated"

    def test_get_stats(self):
        sm = SessionManager()
        sm.set_user("test_user")
        sm.create_session()
        stats = sm.get_stats()
        assert stats["total_sessions"] == 1
        assert stats["active_sessions"] == 1

    def test_close_all(self):
        sm = SessionManager()
        sm.set_user("test_user")
        sm.create_session()
        sm.create_session()
        sm.close_all()
        assert sm.get_stats()["active_sessions"] == 0

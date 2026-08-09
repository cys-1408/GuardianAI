"""Tests for Feature Extraction Engine."""

import pytest
from datetime import datetime
from src.ai.features import FeatureExtractionEngine
from src.behavior.event_aggregator import BehavioralWindow, BehavioralEvent
from src.utils.signals import FeatureVector


class TestFeatureExtraction:
    def setup_method(self):
        self.engine = FeatureExtractionEngine()

    def test_empty_window_returns_none(self):
        window = BehavioralWindow(datetime.now(), 60)
        result = self.engine.extract_features(window)
        assert result is None

    def test_keyboard_features(self):
        window = BehavioralWindow(datetime.now(), 60)
        for i in range(5):
            window.add_event(BehavioralEvent(
                event_type="key_press", timestamp=datetime.now(),
                data={"key_code": 65 + i, "dwell_time": 0.1, "flight_time": 0.2,
                      "is_error": False, "hold_time": 0.15},
                session_id="s1"
            ))
        fv = self.engine.extract_features(window)
        assert fv is not None
        assert len(fv.features) > 0

    def test_mouse_features(self):
        window = BehavioralWindow(datetime.now(), 60)
        for i in range(5):
            window.add_event(BehavioralEvent(
                event_type="mouse_move", timestamp=datetime.now(),
                data={"x": i*10, "y": i*10, "velocity": 100.0, "acceleration": 5.0, "angle": 0.5},
                session_id="s1"
            ))
        window.add_event(BehavioralEvent(
            event_type="mouse_click", timestamp=datetime.now(),
            data={"x": 100, "y": 100, "button": "left"},
            session_id="s1"
        ))
        fv = self.engine.extract_features(window)
        assert fv is not None
        assert len(fv.features) > 0

    def test_scroll_features(self):
        window = BehavioralWindow(datetime.now(), 60)
        for i in range(3):
            window.add_event(BehavioralEvent(
                event_type="scroll", timestamp=datetime.now(),
                data={"delta": 120, "direction": "down", "speed": 50.0},
                session_id="s1"
            ))
        fv = self.engine.extract_features(window)
        assert fv is not None
        assert len(fv.features) > 0

    def test_feature_vector_structure(self):
        window = BehavioralWindow(datetime.now(), 60)
        window.add_event(BehavioralEvent(
            event_type="key_press", timestamp=datetime.now(),
            data={"key_code": 65, "dwell_time": 0.1, "flight_time": 0.2, "is_error": False, "hold_time": 0.15},
            session_id="s1"
        ))
        window.add_event(BehavioralEvent(
            event_type="mouse_move", timestamp=datetime.now(),
            data={"x": 100, "y": 200, "velocity": 150.0, "acceleration": 10.0, "angle": 0.3},
            session_id="s1"
        ))
        fv = self.engine.extract_features(window)
        assert fv is not None
        # Keyboard(12) + Mouse(10) + Scroll(6) + Session(6) + Derived(8) = 42
        assert len(fv.features) == 42

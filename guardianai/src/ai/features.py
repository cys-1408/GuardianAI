"""Feature Extraction Engine - Converts raw behavioral events into numerical features.

Processes behavioral windows and extracts keyboard, mouse, scrolling, session-level,
statistical, and temporal features suitable for machine learning.
"""

import logging
import math
import statistics
from typing import Any, Optional

import numpy as np

from src.utils.signals import BehavioralEvent, FeatureVector, get_signals
from src.behavior.event_aggregator import BehavioralWindow

logger = logging.getLogger(__name__)


class FeatureExtractionEngine:
    """Extracts numerical features from behavioral windows."""

    def __init__(self) -> None:
        self._signals = get_signals()

    def extract_features(self, window: BehavioralWindow) -> Optional[FeatureVector]:
        """Extract feature vector from a behavioral window.

        Args:
            window: Aggregated behavioral window

        Returns:
            Feature vector or None if window is invalid
        """
        try:
            if window.event_count == 0:
                return None

            keyboard_features = self._extract_keyboard_features(window)
            mouse_features = self._extract_mouse_features(window)
            scroll_features = self._extract_scroll_features(window)
            session_features = self._extract_session_features(window)

            # Combine all features
            all_features = (keyboard_features + mouse_features +
                          scroll_features + session_features)

            # Compute derived statistical features
            derived_features = self._extract_derived_features(all_features)

            features = all_features + derived_features

            fv = FeatureVector(
                features=features,
                timestamp=window.start_time,
                session_id=window.session_id,
                source="behavioral_window",
            )
            self._signals.feature_extracted.emit(fv)
            return fv

        except Exception as e:
            logger.error(f"Feature extraction failed: {e}")
            return None

    def _extract_keyboard_features(self, window: BehavioralWindow) -> list[float]:
        """Extract keyboard behavioral features.

        Returns 12 keyboard features:
        [avg_dwell, std_dwell, avg_flight, std_flight, avg_hold, std_hold,
         typing_speed, error_rate, burst_ratio, key_count, pause_freq, rhythm_consistency]
        """
        key_events = window.keyboard_events

        if not key_events:
            return [0.0] * 12

        dwell_times = []
        flight_times = []
        hold_times = []
        error_count = 0
        key_codes = []
        timestamps = []

        for event in key_events:
            data = event.data
            if "dwell_time" in data:
                dwell_times.append(data["dwell_time"])
            if "hold_time" in data:
                hold_times.append(data["hold_time"])
            if "flight_time" in data:
                flight_times.append(data["flight_time"])
            if data.get("is_error", False):
                error_count += 1
            if "key_code" in data:
                key_codes.append(data["key_code"])
            timestamps.append(event.timestamp.timestamp())

        features = [
            statistics.mean(dwell_times) if dwell_times else 0.0,
            statistics.stdev(dwell_times) if len(dwell_times) > 1 else 0.0,
            statistics.mean(flight_times) if flight_times else 0.0,
            statistics.stdev(flight_times) if len(flight_times) > 1 else 0.0,
            statistics.mean(hold_times) if hold_times else 0.0,
            statistics.stdev(hold_times) if len(hold_times) > 1 else 0.0,
            len(key_events) / max(window.duration, 1.0) * 60.0,  # typing speed (keys/min)
            error_count / max(len(key_events), 1),  # error rate
            self._compute_burst_ratio(timestamps),
            len(key_codes),
            self._compute_pause_frequency(timestamps),
            self._compute_rhythm_consistency(dwell_times),
        ]
        return features

    def _extract_mouse_features(self, window: BehavioralWindow) -> list[float]:
        """Extract mouse behavioral features.

        Returns 10 mouse features:
        [avg_velocity, std_velocity, avg_accel, std_accel, avg_curvature,
         click_freq, double_click_ratio, avg_drag_speed, avg_drag_distance, click_distribution_entropy]
        """
        mouse_events = window.mouse_events

        if not mouse_events:
            return [0.0] * 10

        velocities = []
        accelerations = []
        click_times = []
        drag_speeds = []
        drag_distances = []
        button_types = []
        positions = []

        for event in mouse_events:
            data = event.data
            if event.event_type == "mouse_move":
                if "velocity" in data:
                    velocities.append(data["velocity"])
                if "acceleration" in data:
                    accelerations.append(data["acceleration"])
            elif event.event_type == "mouse_click":
                click_times.append(event.timestamp.timestamp())
                if "button" in data:
                    button_types.append(data["button"])
            elif event.event_type == "mouse_drag":
                if "speed" in data:
                    drag_speeds.append(data["speed"])
                if "distance" in data:
                    drag_distances.append(data["distance"])

        # Click distribution entropy
        click_dist = {"left": 0, "right": 0, "middle": 0}
        for btn in button_types:
            if btn in click_dist:
                click_dist[btn] += 1
        total = sum(click_dist.values())
        entropy = 0.0
        if total > 0:
            for count in click_dist.values():
                if count > 0:
                    p = count / total
                    entropy -= p * math.log2(p)

        features = [
            statistics.mean(velocities) if velocities else 0.0,
            statistics.stdev(velocities) if len(velocities) > 1 else 0.0,
            statistics.mean(accelerations) if accelerations else 0.0,
            statistics.stdev(accelerations) if len(accelerations) > 1 else 0.0,
            self._compute_avg_curvature(positions),
            len(click_times) / max(window.duration, 1.0),  # click frequency
            self._compute_double_click_ratio(click_times),
            statistics.mean(drag_speeds) if drag_speeds else 0.0,
            statistics.mean(drag_distances) if drag_distances else 0.0,
            entropy,  # click distribution entropy
        ]
        return features

    def _extract_scroll_features(self, window: BehavioralWindow) -> list[float]:
        """Extract scrolling behavioral features.

        Returns 6 scroll features:
        [scroll_freq, avg_scroll_speed, std_scroll_speed, direction_changes,
         avg_scroll_distance, avg_pause_duration]
        """
        scroll_events = window.scroll_events

        if not scroll_events:
            return [0.0] * 6

        speeds = []
        distances = []
        directions = []
        pause_durations = []
        last_time = None

        for event in scroll_events:
            data = event.data
            if "speed" in data:
                speeds.append(data["speed"])
            distances.append(abs(data.get("delta", 0)))
            directions.append(data.get("direction", "down"))

            if last_time:
                pause = (event.timestamp.timestamp() - last_time)
                if pause > 0.01:
                    pause_durations.append(pause)
            last_time = event.timestamp.timestamp()

        direction_changes = sum(
            1 for i in range(1, len(directions)) if directions[i] != directions[i-1]
        )

        features = [
            len(scroll_events) / max(window.duration, 1.0),  # scroll frequency
            statistics.mean(speeds) if speeds else 0.0,
            statistics.stdev(speeds) if len(speeds) > 1 else 0.0,
            direction_changes,
            statistics.mean(distances) if distances else 0.0,
            statistics.mean(pause_durations) if pause_durations else 0.0,
        ]
        return features

    def _extract_session_features(self, window: BehavioralWindow) -> list[float]:
        """Extract session-level features.

        Returns 6 session features:
        [window_duration, total_events, event_density, keyboard_ratio, mouse_ratio, idle_ratio]
        """
        total = window.event_count
        kbd = len(window.keyboard_events)
        mouse = len(window.mouse_events)
        scroll = len(window.scroll_events)
        idle = len(window.idle_events)

        features = [
            window.duration,
            float(total),
            total / max(window.duration, 1.0),  # event density
            kbd / max(total, 1),  # keyboard ratio
            mouse / max(total, 1),  # mouse ratio
            idle / max(total, 1),  # idle ratio
        ]
        return features

    def _extract_derived_features(self, features: list[float]) -> list[float]:
        """Extract derived statistical features from the feature vector.

        Returns 8 derived features:
        [mean, median, std, variance, min, max, range, entropy]
        """
        if not features:
            return [0.0] * 8

        arr = np.array(features)
        mean = float(np.mean(arr))
        median = float(np.median(arr))
        std = float(np.std(arr))
        var = float(np.var(arr))
        fmin = float(np.min(arr))
        fmax = float(np.max(arr))
        frange = fmax - fmin

        # Approximate entropy of feature distribution
        hist, _ = np.histogram(arr, bins=5)
        hist = hist / max(np.sum(hist), 1)
        entropy = -np.sum(hist * np.log2(hist + 1e-10))

        return [mean, median, std, var, fmin, fmax, frange, float(entropy)]

    def _compute_burst_ratio(self, timestamps: list[float]) -> float:
        """Compute ratio of typing bursts (rapid typing vs pauses)."""
        if len(timestamps) < 2:
            return 0.0
        intervals = [timestamps[i] - timestamps[i-1] for i in range(1, len(timestamps))]
        if not intervals:
            return 0.0
        median_interval = statistics.median(intervals)
        if median_interval <= 0:
            return 0.0
        bursts = sum(1 for i in intervals if i < median_interval * 0.5)
        return bursts / max(len(intervals), 1)

    def _compute_pause_frequency(self, timestamps: list[float]) -> float:
        """Compute frequency of pauses (intervals > 2 seconds)."""
        if len(timestamps) < 2:
            return 0.0
        intervals = [timestamps[i] - timestamps[i-1] for i in range(1, len(timestamps))]
        pauses = sum(1 for i in intervals if i > 2.0)
        return pauses / max(len(intervals), 1)

    def _compute_rhythm_consistency(self, values: list[float]) -> float:
        """Compute rhythm consistency (inverse of CV)."""
        if len(values) < 2:
            return 0.0
        mean = statistics.mean(values)
        std = statistics.stdev(values)
        if mean == 0:
            return 0.0
        return 1.0 / (1.0 + std / mean)

    def _compute_double_click_ratio(self, click_times: list[float]) -> float:
        """Compute ratio of double-clicks."""
        if len(click_times) < 2:
            return 0.0
        double_clicks = sum(
            1 for i in range(1, len(click_times))
            if click_times[i] - click_times[i-1] < 0.5
        )
        return double_clicks / max(len(click_times), 1)

    def _compute_avg_curvature(self, positions: list) -> float:
        """Compute average movement curvature from position data."""
        if len(positions) < 3:
            return 0.0
        total_curvature = 0.0
        for i in range(1, len(positions) - 1):
            dx1 = positions[i][0] - positions[i-1][0]
            dy1 = positions[i][1] - positions[i-1][1]
            dx2 = positions[i+1][0] - positions[i][0]
            dy2 = positions[i+1][1] - positions[i][1]
            cross = abs(dx1 * dy2 - dy1 * dx2)
            dot = dx1 * dx2 + dy1 * dy2
            if dot != 0:
                total_curvature += cross / abs(dot)
        return total_curvature / (len(positions) - 2)

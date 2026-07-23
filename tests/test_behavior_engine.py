"""Tests for behavior_engine — pattern detectors (pure functions, no DB)."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import unittest
from engines.behavior_engine import (
    detect_bet_escalation,
    detect_session_drift,
    detect_losing_clusters,
    detect_recovery_chasing,
    detect_volatility_zones,
)


def _make_event(bet=1.0, win=0.0, balance=100.0):
    return {"bet_amount": bet, "win_amount": win, "balance_after": balance}


class TestBetEscalation(unittest.TestCase):
    def test_no_escalation_flat_bets(self):
        events = [_make_event(bet=1.0, win=0 if i % 3 == 0 else 1.5) for i in range(10)]
        result = detect_bet_escalation(events)
        self.assertFalse(result["detected"])

    def test_escalation_after_losses(self):
        events = []
        for i in range(10):
            if i < 3:
                events.append(_make_event(bet=1.0, win=0.0))
            else:
                # Gradually increasing bets after losses
                events.append(_make_event(bet=1.0 + i * 0.5, win=0.0))
        result = detect_bet_escalation(events)
        self.assertTrue(result["detected"])
        self.assertIn(result["severity"], ["warning", "critical"])

    def test_insufficient_events(self):
        result = detect_bet_escalation([_make_event()])
        self.assertFalse(result["detected"])
        self.assertEqual(result["severity"], "none")


class TestSessionDrift(unittest.TestCase):
    def test_declining_balance(self):
        events = [_make_event(balance=100 - i * 10) for i in range(10)]
        result = detect_session_drift(events)
        self.assertTrue(result["detected"])
        self.assertEqual(result["direction"], "declining")

    def test_stable_balance(self):
        events = [_make_event(balance=100.0) for _ in range(10)]
        result = detect_session_drift(events)
        self.assertFalse(result["detected"])

    def test_insufficient_events(self):
        result = detect_session_drift([_make_event()])
        self.assertFalse(result["detected"])


class TestLosingClusters(unittest.TestCase):
    def test_long_losing_streak(self):
        events = [_make_event(win=0.0) for _ in range(10)]
        result = detect_losing_clusters(events)
        self.assertTrue(result["detected"])
        self.assertGreaterEqual(result["max_streak"], 5)

    def test_no_losing_streak(self):
        events = [_make_event(win=1.0) for _ in range(10)]
        result = detect_losing_clusters(events)
        self.assertFalse(result["detected"])

    def test_mixed_results(self):
        events = [_make_event(win=1.0 if i % 2 == 0 else 0.0) for i in range(10)]
        result = detect_losing_clusters(events)
        self.assertFalse(result["detected"])


class TestRecoveryChasing(unittest.TestCase):
    def test_chasing_after_big_loss(self):
        events = []
        # Use very large bets for big losses to ensure they exceed thresholds
        # Normal bet=1.0, big loss bet=10.0, chase bet=15.0
        # avg_bet will be ~(1*4 + 10*2 + 15*2)/8 = 7.75
        # 1.5x avg = 11.625, 2x avg = 15.5
        # So big loss bet (10.0) must be > 11.625? No, need bigger.
        # Let's use: normal=1.0, big_loss=15.0, chase=20.0
        # avg = (1*4 + 15*2 + 20*2)/8 = 54/8 = 6.75
        # 1.5x = 10.125, 2x = 13.5
        # big_loss=15.0 > 10.125 ✓, chase=20.0 > 13.5 ✓
        for i in range(8):
            if i == 3:
                events.append(_make_event(bet=15.0, win=0.0))
            elif i == 4:
                events.append(_make_event(bet=20.0, win=0.0))
            elif i == 5:
                events.append(_make_event(bet=15.0, win=0.0))
            elif i == 6:
                events.append(_make_event(bet=20.0, win=0.0))
            else:
                events.append(_make_event(bet=1.0, win=1.0))
        result = detect_recovery_chasing(events)
        self.assertTrue(result["detected"])

    def test_no_chasing(self):
        events = [_make_event(bet=1.0, win=1.0) for _ in range(6)]
        result = detect_recovery_chasing(events)
        self.assertFalse(result["detected"])


class TestVolatilityZones(unittest.TestCase):
    def test_high_volatility(self):
        events = []
        # Mostly stable balance with one extreme volatility zone
        for i in range(25):
            if 8 <= i <= 15:
                # Extreme swings in this window
                balance = 100 + (200 if i % 2 == 0 else -200)
            else:
                # Stable balance elsewhere
                balance = 100 + i * 0.1
            events.append(_make_event(balance=balance))
        result = detect_volatility_zones(events, window=5)
        self.assertTrue(result["detected"])

    def test_low_volatility(self):
        events = [_make_event(balance=100.0 + i * 0.01) for i in range(20)]
        result = detect_volatility_zones(events, window=5)
        self.assertFalse(result["detected"])

    def test_insufficient_events(self):
        events = [_make_event(balance=100.0) for _ in range(3)]
        result = detect_volatility_zones(events, window=10)
        self.assertFalse(result["detected"])


if __name__ == "__main__":
    unittest.main()

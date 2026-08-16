"""Tests for live_coach_engine — pattern detectors and Fallback AI triggers."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import unittest
from engines.live_coach_engine import get_coaching_message, reset_coach

def _make_live_event(bet=1.0, win=0.0, balance=100.0, net=0.0):
    return {
        "id": 1,
        "run_id": 1,
        "event_type": "spin",
        "payload": {
            "bet_amount": bet,
            "win_amount": win,
            "balance_after": balance,
            "net_delta": net,
            "ocr_confidence": 0.95
        }
    }

class TestLiveCoach(unittest.TestCase):
    def setUp(self):
        reset_coach()

    def test_no_coaching_under_fire_threshold(self):
        events = [_make_live_event() for _ in range(2)]
        msg = get_coaching_message(events)
        self.assertIsNone(msg)

    def test_martingale_coaching_triggered(self):
        events = [
            _make_live_event(bet=1.0, win=0.0, net=-1.0),
            _make_live_event(bet=2.0, win=0.0, net=-2.0),
            _make_live_event(bet=4.0, win=0.0, net=-4.0),
            _make_live_event(bet=8.0, win=0.0, net=-8.0),
        ]
        msg = get_coaching_message(events, force=True)
        self.assertIsNotNone(msg)
        self.assertEqual(msg["trigger"], "martingale")
        self.assertEqual(msg["type"], "critical")

    def test_rtp_decay_coaching_triggered(self):
        # 15 spins with bet=10 and win=0 -> RTP=0% (critically low)
        events = [_make_live_event(bet=10.0, win=0.0, net=-10.0) for _ in range(15)]
        msg = get_coaching_message(events, force=True)
        self.assertIsNotNone(msg)
        self.assertEqual(msg["trigger"], "rtp_decay")
        self.assertEqual(msg["type"], "warning")

if __name__ == "__main__":
    unittest.main()

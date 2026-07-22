import pytest
from engines.event_validator import validate_session_events, ValidationResult


def _make_event(bet=10.0, win=0.0, balance=100.0, confidence=1.0, ts_offset=0, ev_id=1):
    return {
        "id": ev_id,
        "session_id": 1,
        "timestamp": f"2026-01-01T00:{ts_offset:02d}:00",
        "event_type": "spin",
        "bet_amount": bet,
        "win_amount": win,
        "balance_after": balance,
        "confidence_score": confidence,
    }


class TestBalanceContinuity:
    def test_detects_large_balance_jump(self):
        events = [
            _make_event(bet=10, win=0, balance=b, ts_offset=i, ev_id=i + 1)
            for i, b in enumerate(range(100, -100, -10))
        ] + [
            _make_event(bet=10, win=0, balance=500, ts_offset=20, ev_id=21),
            _make_event(bet=10, win=0, balance=490, ts_offset=21, ev_id=22),
        ]
        result = validate_session_events(events)
        assert len(result.flagged) >= 1
        assert any("balance" in f.reason.lower() for f in result.flagged)

    def test_accepts_normal_balance_curve(self):
        events = [
            _make_event(bet=10, win=0, balance=100, ts_offset=0, ev_id=1),
            _make_event(bet=10, win=15, balance=105, ts_offset=1, ev_id=2),
            _make_event(bet=10, win=0, balance=95, ts_offset=2, ev_id=3),
        ]
        result = validate_session_events(events)
        assert len(result.flagged) == 0


class TestBetWinReconciliation:
    def test_detects_bet_exceeding_balance(self):
        events = [
            _make_event(bet=10, win=0, balance=100, ts_offset=0, ev_id=1),
            _make_event(bet=200, win=0, balance=0, ts_offset=1, ev_id=2),
        ]
        result = validate_session_events(events)
        assert len(result.flagged) >= 1

    def test_detects_impossible_win(self):
        events = [
            _make_event(bet=10, win=0, balance=100, ts_offset=0, ev_id=1),
            _make_event(bet=10, win=99999, balance=100, ts_offset=1, ev_id=2),
        ]
        result = validate_session_events(events)
        assert len(result.flagged) >= 1

    def test_detects_negative_balance(self):
        events = [
            _make_event(bet=10, win=0, balance=100, ts_offset=0, ev_id=1),
            _make_event(bet=10, win=0, balance=-5, ts_offset=1, ev_id=2),
        ]
        result = validate_session_events(events)
        assert len(result.flagged) >= 1


class TestAutoCorrection:
    def test_corrects_single_frame_glitch(self):
        normal = [
            _make_event(bet=10, win=0, balance=b, confidence=0.95, ts_offset=i, ev_id=i + 1)
            for i, b in enumerate(range(100, 0, -10))
        ]
        glitch = _make_event(bet=10, win=0, balance=999, confidence=0.3, ts_offset=10, ev_id=11)
        after = [
            _make_event(bet=10, win=0, balance=b, confidence=0.95, ts_offset=11 + i, ev_id=12 + i)
            for i, b in enumerate(range(9, -200, -10))
        ]
        events = normal + [glitch] + after
        result = validate_session_events(events)
        assert result.auto_corrected >= 1

    def test_does_not_correct_without_context(self):
        events = [
            _make_event(bet=10, win=0, balance=999, confidence=0.3, ts_offset=0, ev_id=1),
        ]
        result = validate_session_events(events)
        assert result.auto_corrected == 0

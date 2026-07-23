"""Tests for trend_engine — rolling trends, streaks, health (uses in-memory DB)."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import unittest
from unittest.mock import patch
import sqlite3

from database.db import SCHEMA_SQL, SCHEMA_V3_SQL


def _in_memory_db():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA_SQL)
    conn.executescript(SCHEMA_V3_SQL)
    return conn


def _seed_session(conn, **kwargs):
    defaults = dict(
        name="Test Session", game_name="Test Game", platform="Test",
        date="2026-01-01", duration_minutes=60, start_balance=100.0,
        end_balance=110.0, total_bets=50.0, total_wins=60.0, net_result=10.0,
        rtp=120.0, spins=50, biggest_win=20.0, biggest_loss=5.0,
        losing_streak=2, status="complete", notes=""
    )
    defaults.update(kwargs)
    cur = conn.execute(
        "INSERT INTO sessions (name,game_name,platform,date,duration_minutes,"
        "start_balance,end_balance,total_bets,total_wins,net_result,rtp,spins,"
        "biggest_win,biggest_loss,losing_streak,status,notes) VALUES "
        "(:name,:game_name,:platform,:date,:duration_minutes,:start_balance,"
        ":end_balance,:total_bets,:total_wins,:net_result,:rtp,:spins,"
        ":biggest_win,:biggest_loss,:losing_streak,:status,:notes)", defaults
    )
    conn.commit()
    return cur.lastrowid


def _seed_events(conn, session_id, count=10):
    for i in range(count):
        balance = 100.0 + i * 5
        conn.execute(
            "INSERT INTO events (session_id, timestamp, event_type, bet_amount, "
            "win_amount, balance_after, confidence_score, source) VALUES (?,?,?,?,?,?,?,?)",
            (session_id, f"2026-01-01T00:{i:02d}:00", "spin", 1.0, 0.5, balance, 0.95, "test")
        )
    conn.commit()


class TestRollingTrends(unittest.TestCase):
    def setUp(self):
        self.conn = _in_memory_db()
        for i in range(5):
            _seed_session(self.conn, rtp=90.0 + i * 3, net_result=-10.0 + i * 5,
                         losing_streak=5 - i, name=f"Session {i}")

    @patch("engines.trend_engine.get_connection")
    def test_get_rolling_trends(self, mock_conn):
        mock_conn.return_value = self.conn
        from engines.trend_engine import get_rolling_trends
        result = get_rolling_trends(last_n=5)
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["sessions_analysed"], 5)
        self.assertIn("trends", result)

    @patch("engines.trend_engine.get_connection")
    def test_get_rolling_trends_insufficient(self, mock_conn):
        mock_conn.return_value = self.conn
        from engines.trend_engine import get_rolling_trends
        result = get_rolling_trends(last_n=1)
        self.assertEqual(result["status"], "insufficient_data")


class TestSessionStreaks(unittest.TestCase):
    def setUp(self):
        self.conn = _in_memory_db()
        _seed_session(self.conn, net_result=10.0)
        _seed_session(self.conn, net_result=-5.0)
        _seed_session(self.conn, net_result=15.0)

    @patch("engines.trend_engine.get_connection")
    def test_get_session_streaks(self, mock_conn):
        mock_conn.return_value = self.conn
        from engines.trend_engine import get_session_streaks
        result = get_session_streaks()
        self.assertIn("current_streak", result)
        self.assertIn("longest_win", result)
        self.assertIn("longest_loss", result)
        self.assertEqual(result["total_sessions"], 3)


class TestSessionHealth(unittest.TestCase):
    def setUp(self):
        self.conn = _in_memory_db()
        self.sid = _seed_session(self.conn, rtp=100.0, losing_streak=2, spins=100)
        _seed_events(self.conn, self.sid)

    @patch("engines.trend_engine.get_connection")
    def test_get_session_health(self, mock_conn):
        mock_conn.return_value = self.conn
        from engines.trend_engine import get_session_health
        result = get_session_health(self.sid)
        self.assertIn("health_score", result)
        self.assertIn("health_level", result)
        self.assertGreaterEqual(result["health_score"], 0)
        self.assertLessEqual(result["health_score"], 100)

    @patch("engines.trend_engine.get_connection")
    def test_session_not_found(self, mock_conn):
        mock_conn.return_value = self.conn
        from engines.trend_engine import get_session_health
        result = get_session_health(9999)
        self.assertIn("error", result)


class TestEarlyWarnings(unittest.TestCase):
    def setUp(self):
        self.conn = _in_memory_db()
        self.sid = _seed_session(self.conn, rtp=80.0, losing_streak=12, end_balance=20.0)
        _seed_events(self.conn, self.sid)

    @patch("engines.trend_engine.get_connection")
    def test_get_early_warnings(self, mock_conn):
        mock_conn.return_value = self.conn
        from engines.trend_engine import get_early_warnings
        warnings = get_early_warnings(self.sid)
        self.assertIsInstance(warnings, list)


class TestProjectDrift(unittest.TestCase):
    def setUp(self):
        self.conn = _in_memory_db()
        self.sid = _seed_session(self.conn)
        _seed_events(self.conn, self.sid, count=10)

    @patch("engines.trend_engine.get_connection")
    def test_project_session_drift(self, mock_conn):
        mock_conn.return_value = self.conn
        from engines.trend_engine import project_session_drift
        result = project_session_drift(self.sid)
        self.assertIn("status", result)
        self.assertIn("projected_next", result)


if __name__ == "__main__":
    unittest.main()

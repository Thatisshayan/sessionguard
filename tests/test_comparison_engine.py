"""Tests for comparison_engine — multi-session diff (uses in-memory DB)."""
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


class TestComparison(unittest.TestCase):
    def setUp(self):
        self.conn = _in_memory_db()
        self.sid1 = _seed_session(self.conn, name="Session 1", rtp=95.0, net_result=-5.0, losing_streak=3)
        self.sid2 = _seed_session(self.conn, name="Session 2", rtp=110.0, net_result=20.0, losing_streak=1)

    @patch("engines.comparison_engine.get_connection")
    def test_compare_two_sessions(self, mock_conn):
        mock_conn.return_value = self.conn
        from engines.comparison_engine import compare_sessions
        result = compare_sessions([self.sid1, self.sid2])
        self.assertIn("sessions", result)
        self.assertIn("diff", result)
        self.assertIn("narrative", result)
        self.assertEqual(len(result["sessions"]), 2)

    @patch("engines.comparison_engine.get_connection")
    def test_compare_insufficient_sessions(self, mock_conn):
        mock_conn.return_value = self.conn
        from engines.comparison_engine import compare_sessions
        result = compare_sessions([self.sid1])
        self.assertIn("error", result)

    @patch("engines.comparison_engine.get_connection")
    def test_compare_no_sessions(self, mock_conn):
        mock_conn.return_value = self.conn
        from engines.comparison_engine import compare_sessions
        result = compare_sessions([])
        self.assertIn("error", result)


if __name__ == "__main__":
    unittest.main()

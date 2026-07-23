"""Tests for analysis_engine — global + session metrics (uses in-memory DB)."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import unittest
from unittest.mock import patch
import sqlite3

from database.db import SCHEMA_SQL, SCHEMA_V2_SQL, SCHEMA_V3_SQL, SCHEMA_V5_SQL, SCHEMA_V6_SQL


def _in_memory_db():
    """Create an in-memory SQLite DB with the full schema."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA_SQL)
    conn.executescript(SCHEMA_V2_SQL)
    conn.executescript(SCHEMA_V3_SQL)
    conn.executescript(SCHEMA_V5_SQL)
    conn.executescript(SCHEMA_V6_SQL)
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


class TestGlobalMetrics(unittest.TestCase):
    def setUp(self):
        self.conn = _in_memory_db()
        _seed_session(self.conn, rtp=95.0, net_result=-5.0, spins=100)
        _seed_session(self.conn, rtp=105.0, net_result=15.0, spins=50)

    @patch("engines.analysis_engine.get_connection")
    def test_get_global_metrics(self, mock_conn):
        mock_conn.return_value = self.conn
        from engines.analysis_engine import get_global_metrics
        result = get_global_metrics()
        self.assertEqual(result["total_sessions"], 2)
        self.assertAlmostEqual(result["avg_rtp"], 100.0)
        self.assertAlmostEqual(result["total_net"], 10.0)

    @patch("engines.analysis_engine.get_connection")
    def test_get_rtp_distribution(self, mock_conn):
        mock_conn.return_value = self.conn
        from engines.analysis_engine import get_rtp_distribution
        result = get_rtp_distribution()
        self.assertIsInstance(result, list)
        total = sum(r["count"] for r in result)
        self.assertEqual(total, 2)

    @patch("engines.analysis_engine.get_connection")
    def test_get_net_result_over_time(self, mock_conn):
        mock_conn.return_value = self.conn
        from engines.analysis_engine import get_net_result_over_time
        result = get_net_result_over_time()
        self.assertIsInstance(result, list)

    @patch("engines.analysis_engine.get_connection")
    def test_get_performance_by_game(self, mock_conn):
        mock_conn.return_value = self.conn
        from engines.analysis_engine import get_performance_by_game
        result = get_performance_by_game()
        self.assertIsInstance(result, list)


class TestSessionMetrics(unittest.TestCase):
    def setUp(self):
        self.conn = _in_memory_db()
        self.sid = _seed_session(self.conn, rtp=90.0, net_result=-10.0)

    @patch("engines.analysis_engine.get_connection")
    def test_get_session_metrics_found(self, mock_conn):
        mock_conn.return_value = self.conn
        from engines.analysis_engine import get_session_metrics
        result = get_session_metrics(self.sid)
        self.assertIsNotNone(result)
        self.assertEqual(result["id"], self.sid)

    @patch("engines.analysis_engine.get_connection")
    def test_get_session_metrics_not_found(self, mock_conn):
        mock_conn.return_value = self.conn
        from engines.analysis_engine import get_session_metrics
        result = get_session_metrics(9999)
        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()

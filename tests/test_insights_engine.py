"""Tests for insights_engine — rule-based insights (uses in-memory DB)."""
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


class TestInsights(unittest.TestCase):
    def setUp(self):
        self.conn = _in_memory_db()

    @patch("engines.insights_engine.get_connection")
    def test_generate_insights_low_rtp(self, mock_conn):
        mock_conn.return_value = self.conn
        sid = _seed_session(self.conn, rtp=80.0, losing_streak=20)
        from engines.insights_engine import generate_and_persist_insights
        insights = generate_and_persist_insights(sid)
        self.assertGreater(len(insights), 0)
        severities = [i["severity"] for i in insights]
        self.assertIn("critical", severities)

    @patch("engines.insights_engine.get_connection")
    def test_generate_insights_good_session(self, mock_conn):
        mock_conn.return_value = self.conn
        sid = _seed_session(self.conn, rtp=105.0, losing_streak=1)
        from engines.insights_engine import generate_and_persist_insights
        insights = generate_and_persist_insights(sid)
        self.assertIsInstance(insights, list)

    @patch("engines.insights_engine.get_connection")
    def test_get_insights_empty(self, mock_conn):
        mock_conn.return_value = self.conn
        from engines.insights_engine import get_insights
        insights = get_insights()
        self.assertIsInstance(insights, list)

    @patch("engines.insights_engine.get_connection")
    def test_session_not_found(self, mock_conn):
        mock_conn.return_value = self.conn
        from engines.insights_engine import generate_and_persist_insights
        insights = generate_and_persist_insights(9999)
        self.assertEqual(insights, [])


if __name__ == "__main__":
    unittest.main()

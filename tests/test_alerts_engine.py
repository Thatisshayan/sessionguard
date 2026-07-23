"""Tests for alerts_engine — threshold alerts (uses in-memory DB)."""
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


class TestGetAlerts(unittest.TestCase):
    def setUp(self):
        self.conn = _in_memory_db()
        self.sid = _seed_session(self.conn, rtp=80.0, net_result=-250.0, losing_streak=20)

    @patch("engines.alerts_engine.get_connection")
    def test_generate_and_persist_alerts(self, mock_conn):
        mock_conn.return_value = self.conn
        from engines.alerts_engine import generate_and_persist_alerts
        alerts = generate_and_persist_alerts(self.sid)
        self.assertGreater(len(alerts), 0)
        severities = [a["severity"] for a in alerts]
        self.assertIn("critical", severities)

    @patch("engines.alerts_engine.get_connection")
    def test_acknowledge_nonexistent(self, mock_conn):
        mock_conn.return_value = self.conn
        from engines.alerts_engine import acknowledge_alert
        result = acknowledge_alert(9999)
        self.assertFalse(result)

    @patch("engines.alerts_engine.get_connection")
    def test_get_alert_summary_empty(self, mock_conn):
        mock_conn.return_value = self.conn
        from engines.alerts_engine import get_alert_summary
        summary = get_alert_summary()
        self.assertIn("total", summary)
        self.assertEqual(summary["total"], 0)

    @patch("engines.alerts_engine.get_connection")
    def test_session_not_found(self, mock_conn):
        mock_conn.return_value = self.conn
        from engines.alerts_engine import generate_and_persist_alerts
        alerts = generate_and_persist_alerts(9999)
        self.assertEqual(alerts, [])

    @patch("engines.alerts_engine.get_connection")
    def test_get_alerts_empty(self, mock_conn):
        mock_conn.return_value = self.conn
        from engines.alerts_engine import get_alerts
        alerts = get_alerts()
        self.assertIsInstance(alerts, list)


if __name__ == "__main__":
    unittest.main()

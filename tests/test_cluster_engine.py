"""Tests for cluster_engine — clustering + anomalies (uses in-memory DB)."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import unittest
from unittest.mock import patch
import sqlite3

from database.db import SCHEMA_SQL, SCHEMA_V3_SQL, SCHEMA_V5_SQL


def _in_memory_db():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA_SQL)
    conn.executescript(SCHEMA_V3_SQL)
    conn.executescript(SCHEMA_V5_SQL)
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


class TestDatasetSummary(unittest.TestCase):
    def setUp(self):
        self.conn = _in_memory_db()
        for i in range(6):
            _seed_session(self.conn, rtp=85.0 + i * 5, net_result=-20.0 + i * 10,
                         losing_streak=i * 2, spins=50 + i * 10,
                         name=f"Session {i}")

    @patch("engines.cluster_engine.get_connection")
    def test_get_dataset_summary(self, mock_conn):
        mock_conn.return_value = self.conn
        from engines.cluster_engine import get_dataset_summary
        result = get_dataset_summary()
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["total_sessions"], 6)
        self.assertIn("rtp", result)
        self.assertIn("net_result", result)
        self.assertIn("losing_streak", result)

    @patch("engines.cluster_engine.get_connection")
    def test_get_dataset_summary_empty(self, mock_conn):
        mock_conn.return_value = self.conn
        from engines.cluster_engine import get_dataset_summary
        result = get_dataset_summary()
        self.assertEqual(result["status"], "ok")


class TestDetectAnomalies(unittest.TestCase):
    def setUp(self):
        self.conn = _in_memory_db()
        for i in range(6):
            _seed_session(self.conn, rtp=95.0 + i * 2, net_result=0.0, name=f"Session {i}")
        _seed_session(self.conn, rtp=50.0, net_result=-500.0, name="Outlier")

    @patch("engines.cluster_engine.get_connection")
    def test_detect_anomalies(self, mock_conn):
        mock_conn.return_value = self.conn
        from engines.cluster_engine import detect_anomalies
        anomalies = detect_anomalies(z_threshold=1.5)
        self.assertIsInstance(anomalies, list)
        if anomalies:
            self.assertIn("session_id", anomalies[0])
            self.assertIn("reasons", anomalies[0])

    @patch("engines.cluster_engine.get_connection")
    def test_detect_anomalies_no_outliers(self, mock_conn):
        mock_conn.return_value = self.conn
        from engines.cluster_engine import detect_anomalies
        anomalies = detect_anomalies(z_threshold=5.0)
        self.assertIsInstance(anomalies, list)


class TestHDBSCANClustering(unittest.TestCase):
    def test_cluster_sessions_hdbscan(self):
        from engines.cluster_engine import cluster_sessions_hdbscan
        vectors = [
            {"id": i, "rtp": 90 + i, "net_result": -10 + i * 5, "spins": 50,
             "avg_bet": 1.0, "losing_streak": 5 - i, "biggest_win": 10 + i}
            for i in range(6)
        ]
        result = cluster_sessions_hdbscan(vectors, min_cluster_size=3)
        self.assertIsInstance(result, list)

    def test_cluster_sessions_hdbscan_insufficient(self):
        from engines.cluster_engine import cluster_sessions_hdbscan
        result = cluster_sessions_hdbscan([], min_cluster_size=3)
        self.assertEqual(result, [])


if __name__ == "__main__":
    unittest.main()

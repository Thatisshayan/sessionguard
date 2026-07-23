"""Tests for review_queue_engine — review queue (uses in-memory DB)."""
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


def _seed_review_item(conn, session_id, event_id=None):
    cur = conn.execute(
        "INSERT INTO review_items (session_id, event_id, reason, status) VALUES (?,?,?,?)",
        (session_id, event_id, "Low confidence OCR", "pending")
    )
    conn.commit()
    return cur.lastrowid


class TestReviewQueue(unittest.TestCase):
    def setUp(self):
        self.conn = _in_memory_db()
        self.sid = _seed_session(self.conn)
        self.riid = _seed_review_item(self.conn, self.sid)

    @patch("engines.review_queue_engine.get_connection")
    def test_get_review_queue(self, mock_conn):
        mock_conn.return_value = self.conn
        from engines.review_queue_engine import get_review_queue
        items = get_review_queue()
        self.assertGreater(len(items), 0)

    @patch("engines.review_queue_engine.get_connection")
    def test_resolve_accept(self, mock_conn):
        mock_conn.return_value = self.conn
        from engines.review_queue_engine import resolve_review_item
        result = resolve_review_item(self.riid, "accepted")
        self.assertTrue(result)

    @patch("engines.review_queue_engine.get_connection")
    def test_resolve_reject(self, mock_conn):
        mock_conn.return_value = self.conn
        from engines.review_queue_engine import resolve_review_item
        result = resolve_review_item(self.riid, "rejected")
        self.assertTrue(result)

    @patch("engines.review_queue_engine.get_connection")
    def test_resolve_corrected(self, mock_conn):
        mock_conn.return_value = self.conn
        from engines.review_queue_engine import resolve_review_item
        result = resolve_review_item(self.riid, "corrected", corrected_value="5.50")
        self.assertTrue(result)

    @patch("engines.review_queue_engine.get_connection")
    def test_resolve_invalid_action(self, mock_conn):
        mock_conn.return_value = self.conn
        from engines.review_queue_engine import resolve_review_item
        result = resolve_review_item(self.riid, "invalid")
        self.assertFalse(result)

    @patch("engines.review_queue_engine.get_connection")
    def test_resolve_not_found(self, mock_conn):
        mock_conn.return_value = self.conn
        from engines.review_queue_engine import resolve_review_item
        result = resolve_review_item(9999, "accepted")
        self.assertFalse(result)

    @patch("engines.review_queue_engine.get_connection")
    def test_get_queue_summary(self, mock_conn):
        mock_conn.return_value = self.conn
        from engines.review_queue_engine import get_queue_summary
        summary = get_queue_summary()
        self.assertIn("total", summary)
        self.assertIn("pending", summary)
        self.assertGreaterEqual(summary["total"], 1)


if __name__ == "__main__":
    unittest.main()

"""Tests for insights_engine — rule-based insights (async, uses a temp-file DB).

insights_engine is natively async (aiosqlite) as of TASK-031's async engine
hardening. See tests/test_alerts_engine.py for why a temp file is used
instead of :memory: or mocking.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import sqlite3
import tempfile
import unittest
from pathlib import Path

import database.db as db_module
from database.db import SCHEMA_SQL, SCHEMA_V3_SQL


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


class TestInsights(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self._orig_db_path = db_module.DB_PATH
        db_module.DB_PATH = Path(self._tmpdir.name) / "test.db"

        self.conn = sqlite3.connect(str(db_module.DB_PATH))
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(SCHEMA_SQL)
        self.conn.executescript(SCHEMA_V3_SQL)

    def tearDown(self):
        self.conn.close()
        db_module.DB_PATH = self._orig_db_path
        self._tmpdir.cleanup()

    async def test_generate_insights_low_rtp(self):
        sid = _seed_session(self.conn, rtp=80.0, losing_streak=20)
        from engines.insights_engine import generate_and_persist_insights
        insights = await generate_and_persist_insights(sid)
        self.assertGreater(len(insights), 0)
        severities = [i["severity"] for i in insights]
        self.assertIn("critical", severities)

    async def test_generate_insights_good_session(self):
        sid = _seed_session(self.conn, rtp=105.0, losing_streak=1)
        from engines.insights_engine import generate_and_persist_insights
        insights = await generate_and_persist_insights(sid)
        self.assertIsInstance(insights, list)

    async def test_get_insights_empty(self):
        from engines.insights_engine import get_insights
        insights = await get_insights()
        self.assertIsInstance(insights, list)

    async def test_session_not_found(self):
        from engines.insights_engine import generate_and_persist_insights
        insights = await generate_and_persist_insights(9999)
        self.assertEqual(insights, [])


if __name__ == "__main__":
    unittest.main()

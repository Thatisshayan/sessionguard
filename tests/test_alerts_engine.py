"""Tests for alerts_engine — threshold alerts (async, uses a temp-file DB).

alerts_engine is natively async (aiosqlite) as of TASK-031's async engine
hardening. Each aiosqlite connection opens the DB file fresh, so a shared
:memory: database (visible only within the connection that created it)
doesn't work across the engine's multiple connections per test - a real
temp file does, and it's a more honest end-to-end test of the actual
async DB path than mocking would be.
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


class TestGetAlerts(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self._orig_db_path = db_module.DB_PATH
        db_module.DB_PATH = Path(self._tmpdir.name) / "test.db"

        conn = sqlite3.connect(str(db_module.DB_PATH))
        conn.row_factory = sqlite3.Row
        conn.executescript(SCHEMA_SQL)
        conn.executescript(SCHEMA_V3_SQL)
        self.sid = _seed_session(conn, rtp=80.0, net_result=-250.0, losing_streak=20)
        conn.close()

    def tearDown(self):
        db_module.DB_PATH = self._orig_db_path
        self._tmpdir.cleanup()

    async def test_generate_and_persist_alerts(self):
        from engines.alerts_engine import generate_and_persist_alerts
        alerts = await generate_and_persist_alerts(self.sid)
        self.assertGreater(len(alerts), 0)
        severities = [a["severity"] for a in alerts]
        self.assertIn("critical", severities)

    async def test_acknowledge_nonexistent(self):
        from engines.alerts_engine import acknowledge_alert
        result = await acknowledge_alert(9999)
        self.assertFalse(result)

    async def test_get_alert_summary_empty(self):
        from engines.alerts_engine import get_alert_summary
        summary = await get_alert_summary()
        self.assertIn("total", summary)
        self.assertEqual(summary["total"], 0)

    async def test_session_not_found(self):
        from engines.alerts_engine import generate_and_persist_alerts
        alerts = await generate_and_persist_alerts(9999)
        self.assertEqual(alerts, [])

    async def test_get_alerts_empty(self):
        from engines.alerts_engine import get_alerts
        alerts = await get_alerts()
        self.assertIsInstance(alerts, list)


if __name__ == "__main__":
    unittest.main()

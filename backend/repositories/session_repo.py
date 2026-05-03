"""
backend/repositories/session_repo.py
--------------------------------------
Repository pattern for session data access.
Abstracts raw SQL so switching to PostgreSQL (asyncpg + SQLAlchemy) means
only rewriting this file — routes and engines stay unchanged.

Maturity: Working Prototype (SQLite)
Future:   Replace body with async SQLAlchemy 2.0 sessions for PostgreSQL (V7).
"""

from __future__ import annotations
from database.db import get_connection


class SessionRepository:
    """All session DB operations go through here."""

    @staticmethod
    def get_all(
        status:    str | None = None,
        game_name: str | None = None,
        platform:  str | None = None,
        limit:     int        = 100,
    ) -> list[dict]:
        conn    = get_connection()
        filters = []
        params  = []
        if status:    filters.append("status=?");    params.append(status)
        if game_name: filters.append("game_name=?"); params.append(game_name)
        if platform:  filters.append("platform=?");  params.append(platform)
        where  = ("WHERE " + " AND ".join(filters)) if filters else ""
        rows   = conn.execute(
            f"SELECT * FROM sessions {where} ORDER BY date DESC, id DESC LIMIT ?",
            [*params, limit]
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    @staticmethod
    def get_by_id(session_id: int) -> dict | None:
        conn = get_connection()
        row  = conn.execute("SELECT * FROM sessions WHERE id=?", (session_id,)).fetchone()
        conn.close()
        return dict(row) if row else None

    @staticmethod
    def create(data: dict) -> int:
        conn = get_connection()
        cur  = conn.execute(
            """INSERT INTO sessions
               (name,game_name,platform,date,duration_minutes,start_balance,
                end_balance,total_bets,total_wins,net_result,rtp,spins,
                biggest_win,biggest_loss,losing_streak,status,notes)
               VALUES
               (:name,:game_name,:platform,:date,:duration_minutes,:start_balance,
                :end_balance,:total_bets,:total_wins,:net_result,:rtp,:spins,
                :biggest_win,:biggest_loss,:losing_streak,:status,:notes)""",
            data
        )
        session_id = cur.lastrowid
        conn.commit(); conn.close()
        return session_id

    @staticmethod
    def update(session_id: int, updates: dict) -> bool:
        if not updates:
            return True
        conn       = get_connection()
        set_clause = ", ".join(f"{k}=?" for k in updates)
        cur        = conn.execute(
            f"UPDATE sessions SET {set_clause} WHERE id=?",
            [*updates.values(), session_id]
        )
        conn.commit(); conn.close()
        return cur.rowcount > 0

    @staticmethod
    def delete(session_id: int) -> bool:
        conn = get_connection()
        cur  = conn.execute("DELETE FROM sessions WHERE id=?", (session_id,))
        conn.commit(); conn.close()
        return cur.rowcount > 0

    @staticmethod
    def get_stats() -> dict:
        conn = get_connection()
        row  = conn.execute("""
            SELECT COUNT(*) AS total,
                   ROUND(AVG(rtp),2) AS avg_rtp,
                   ROUND(SUM(net_result),2) AS total_net,
                   SUM(spins) AS total_spins,
                   COUNT(CASE WHEN status='flagged' THEN 1 END) AS flagged
            FROM sessions
        """).fetchone()
        conn.close()
        return dict(row)


class EventRepository:
    """All event DB operations."""

    @staticmethod
    def get_for_session(session_id: int, limit: int = 2000) -> list[dict]:
        conn = get_connection()
        rows = conn.execute(
            "SELECT * FROM events WHERE session_id=? ORDER BY timestamp LIMIT ?",
            (session_id, limit)
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    @staticmethod
    def create_bulk(events: list[dict]) -> int:
        if not events:
            return 0
        conn = get_connection()
        conn.executemany(
            """INSERT INTO events
               (session_id,timestamp,event_type,bet_amount,win_amount,
                balance_after,confidence_score,source)
               VALUES
               (:session_id,:timestamp,:event_type,:bet_amount,:win_amount,
                :balance_after,:confidence_score,:source)""",
            events
        )
        count = len(events)
        conn.commit(); conn.close()
        return count

    @staticmethod
    def summary(session_id: int) -> dict:
        conn = get_connection()
        row  = conn.execute("""
            SELECT COUNT(*) AS total,
                   COUNT(CASE WHEN win_amount>0 THEN 1 END) AS winning,
                   ROUND(AVG(bet_amount),2) AS avg_bet,
                   ROUND(MAX(win_amount),2) AS biggest_win,
                   ROUND(AVG(confidence_score),3) AS avg_confidence
            FROM events WHERE session_id=?
        """, (session_id,)).fetchone()
        conn.close()
        return dict(row) if row else {}

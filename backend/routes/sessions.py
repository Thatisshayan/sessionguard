"""
backend/routes/sessions.py
---------------------------
Session CRUD endpoints. Thin — delegates to DB and engines.

Maturity: Working Prototype (GET list/detail, POST create, PATCH update)
Future:   Add pagination, advanced filtering, project grouping (V6+).
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional
from database.db import get_connection
from engines.analysis_engine import get_session_metrics
from engines.insights_engine import generate_and_persist_insights
from engines.alerts_engine import generate_and_persist_alerts

router = APIRouter(tags=["sessions"])


class SessionCreate(BaseModel):
    name: str
    game_name: str
    platform: str
    date: str
    duration_minutes: int = 0
    start_balance: float
    end_balance: float
    total_bets: float = 0
    total_wins: float = 0
    spins: int = 0
    biggest_win: float = 0
    biggest_loss: float = 0
    losing_streak: int = 0
    notes: str = ""


class SessionUpdate(BaseModel):
    notes: Optional[str] = None
    status: Optional[str] = None


@router.get("")
def list_sessions(
    skip:   int = Query(0, ge=0),
    status:    Optional[str] = Query(None),
    game_name: Optional[str] = Query(None),
    platform:  Optional[str] = Query(None),
    limit:     int           = Query(100, le=500),
):
    """List sessions with optional filters. Returns newest first."""
    conn = get_connection()
    filters, params = [], []

    if status:
        filters.append("status = ?")
        params.append(status)
    if game_name:
        filters.append("game_name = ?")
        params.append(game_name)
    if platform:
        filters.append("platform = ?")
        params.append(platform)

    where = ("WHERE " + " AND ".join(filters)) if filters else ""
    rows = conn.execute(
        f"SELECT * FROM sessions {where} ORDER BY date DESC, created_at DESC LIMIT ?",
        [*params, limit]
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


@router.get("/{session_id}")
def get_session(session_id: int):
    """Return detailed metrics for one session."""
    result = get_session_metrics(session_id)
    if not result:
        raise HTTPException(status_code=404, detail="Session not found.")
    return result


@router.post("", status_code=201)
def create_session(body: SessionCreate):
    """Create a new session and auto-generate insights + alerts."""
    conn = get_connection()
    data = body.dict()
    data["net_result"] = round(data["end_balance"] - data["start_balance"], 2)
    data["rtp"] = (
        round(data["total_wins"] / data["total_bets"] * 100, 2)
        if data["total_bets"] > 0 else 0.0
    )
    data["status"] = "complete"

    cur = conn.execute(
        "INSERT INTO sessions (name,game_name,platform,date,duration_minutes,"
        "start_balance,end_balance,total_bets,total_wins,net_result,rtp,spins,"
        "biggest_win,biggest_loss,losing_streak,status,notes) VALUES "
        "(:name,:game_name,:platform,:date,:duration_minutes,:start_balance,"
        ":end_balance,:total_bets,:total_wins,:net_result,:rtp,:spins,"
        ":biggest_win,:biggest_loss,:losing_streak,:status,:notes)",
        data
    )
    session_id = cur.lastrowid
    conn.commit()
    conn.close()

    # Auto-generate insights and alerts for new session
    generate_and_persist_insights(session_id)
    generate_and_persist_alerts(session_id)

    return {"id": session_id, "message": "Session created.", **data}


@router.patch("/{session_id}")
def update_session(session_id: int, body: SessionUpdate):
    """Update mutable fields on an existing session."""
    conn = get_connection()
    existing = conn.execute("SELECT id FROM sessions WHERE id = ?", (session_id,)).fetchone()
    if not existing:
        conn.close()
        raise HTTPException(status_code=404, detail="Session not found.")

    updates = {k: v for k, v in body.dict().items() if v is not None}
    if not updates:
        conn.close()
        return {"message": "Nothing to update."}

    set_clause = ", ".join(f"{k} = ?" for k in updates)
    conn.execute(
        f"UPDATE sessions SET {set_clause} WHERE id = ?",
        [*updates.values(), session_id]
    )
    conn.commit()
    conn.close()
    return {"id": session_id, "updated": list(updates.keys())}


@router.delete("/{session_id}", status_code=204)
def delete_session(session_id: int):
    """Delete a session and all cascaded data."""
    conn = get_connection()
    cur = conn.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
    conn.commit()
    conn.close()
    if cur.rowcount == 0:
        raise HTTPException(status_code=404, detail="Session not found.")


@router.get("/{session_id}/ocr-results")
def get_session_ocr_results(session_id: int, limit: int = 100):
    """Return OCR results for a session — used by Video Lab page."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM ocr_results WHERE session_id=? ORDER BY id LIMIT ?",
        (session_id, limit)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]

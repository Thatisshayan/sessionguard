"""
backend/routes/sessions.py
---------------------------
Session CRUD endpoints. Thin — delegates to DB and engines.
Uses async DB operations for non-blocking I/O.

Maturity: Working Prototype (GET list/detail, POST create, PATCH update)
Future:   Add pagination, advanced filtering, project grouping (V6+).
"""

import asyncio
from fastapi import APIRouter, HTTPException, Query, Request, Header
from pydantic import BaseModel
from typing import Optional
from database.db import get_connection, async_fetch_all, async_fetch_one, async_execute
from engines.analysis_engine import get_session_metrics
from engines.insights_engine import generate_and_persist_insights
from engines.alerts_engine import generate_and_persist_alerts
from backend.auth.access import require_current_user, require_session_access

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
async def list_sessions(
    skip:   int = Query(0, ge=0),
    status:    Optional[str] = Query(None),
    game_name: Optional[str] = Query(None),
    platform:  Optional[str] = Query(None),
    limit:     int           = Query(100, le=500),
    authorization: Optional[str] = Header(None, alias="Authorization"),
):
    """List sessions with optional filters. Returns newest first."""
    current_user = require_current_user(authorization)
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

    where_parts = []
    where_parts.extend(filters)
    if current_user["role"] != "admin":
        where_parts.append("""
            (
                s.owner_id = ?
                OR EXISTS (
                    SELECT 1
                    FROM session_projects sp
                    JOIN project_members pm ON pm.project_id = sp.project_id
                    WHERE sp.session_id = s.id AND pm.user_id = ?
                )
            )
        """.strip())
        params.extend([current_user["user_id"], current_user["user_id"]])

    where = "WHERE " + " AND ".join(where_parts) if where_parts else ""
    rows = await async_fetch_all(
        f"""
        SELECT s.*
        FROM sessions s
        {where}
        ORDER BY s.date DESC, s.created_at DESC LIMIT ?
        """,
        (*params, limit)
    )
    return rows


@router.get("/{session_id}")
async def get_session(session_id: int, authorization: Optional[str] = Header(None, alias="Authorization")):
    """Return detailed metrics for one session."""
    await require_session_access(session_id, authorization)
    result = await asyncio.to_thread(get_session_metrics, session_id)
    if not result:
        raise HTTPException(status_code=404, detail="Session not found.")
    return result


@router.post("", status_code=201)
async def create_session(body: SessionCreate, request: Request):
    """Create a new session and auto-generate insights + alerts."""
    current_user = getattr(request.state, "current_user", None)
    data = body.dict()
    data["owner_id"] = current_user["user_id"] if current_user else None
    data["net_result"] = round(data["end_balance"] - data["start_balance"], 2)
    data["rtp"] = (
        round(data["total_wins"] / data["total_bets"] * 100, 2)
        if data["total_bets"] > 0 else 0.0
    )
    data["status"] = "complete"

    session_id = await async_execute(
        "INSERT INTO sessions (owner_id,name,game_name,platform,date,duration_minutes,"
        "start_balance,end_balance,total_bets,total_wins,net_result,rtp,spins,"
        "biggest_win,biggest_loss,losing_streak,status,notes) VALUES "
        "(:owner_id,:name,:game_name,:platform,:date,:duration_minutes,:start_balance,"
        ":end_balance,:total_bets,:total_wins,:net_result,:rtp,:spins,"
        ":biggest_win,:biggest_loss,:losing_streak,:status,:notes)",
        data
    )

    # Auto-generate insights and alerts for new session
    await asyncio.to_thread(generate_and_persist_insights, session_id)
    await asyncio.to_thread(generate_and_persist_alerts, session_id)

    return {"id": session_id, "message": "Session created.", **data}


@router.patch("/{session_id}")
async def update_session(session_id: int, body: SessionUpdate, authorization: Optional[str] = Header(None, alias="Authorization")):
    """Update mutable fields on an existing session."""
    await require_session_access(session_id, authorization)
    existing = await async_fetch_one("SELECT id FROM sessions WHERE id = ?", (session_id,))
    if not existing:
        raise HTTPException(status_code=404, detail="Session not found.")

    updates = {k: v for k, v in body.dict().items() if v is not None}
    if not updates:
        return {"message": "Nothing to update."}

    set_clause = ", ".join(f"{k} = ?" for k in updates)
    await async_execute(
        f"UPDATE sessions SET {set_clause} WHERE id = ?",
        (*updates.values(), session_id)
    )
    return {"id": session_id, "updated": list(updates.keys())}


@router.delete("/{session_id}", status_code=204)
async def delete_session(session_id: int, authorization: Optional[str] = Header(None, alias="Authorization")):
    """Delete a session and all cascaded data."""
    await require_session_access(session_id, authorization)
    rowcount = await async_execute("DELETE FROM sessions WHERE id = ?", (session_id,))
    if rowcount == 0:
        raise HTTPException(status_code=404, detail="Session not found.")


@router.get("/{session_id}/ocr-results")
async def get_session_ocr_results(session_id: int, limit: int = 100, authorization: Optional[str] = Header(None, alias="Authorization")):
    """Return OCR results for a session — used by Video Lab page."""
    await require_session_access(session_id, authorization)
    rows = await async_fetch_all(
        "SELECT * FROM ocr_results WHERE session_id=? ORDER BY id LIMIT ?",
        (session_id, limit)
    )
    return rows

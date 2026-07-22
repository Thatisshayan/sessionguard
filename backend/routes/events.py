"""
backend/routes/events.py
------------------------
Event timeline endpoints. Real data from DB.
Maturity: Working Prototype
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from database.db import get_connection
from engines.event_validator import validate_session_events

router = APIRouter(tags=["events"])


@router.get("")
def get_session_events(
    session_id: int = Query(...),
    limit: int      = Query(500, le=2000),
    source: Optional[str] = Query(None),
):
    """
    Return all events for a session — full timeline for charts.
    Adds spin_number and cumulative balance column.
    """
    conn = get_connection()
    s = conn.execute("SELECT id FROM sessions WHERE id=?", (session_id,)).fetchone()
    if not s:
        conn.close()
        raise HTTPException(status_code=404, detail="Session not found.")

    base_q = "SELECT * FROM events WHERE session_id=?"
    params: list = [session_id]
    if source:
        base_q += " AND source=?"
        params.append(source)

    rows = conn.execute(f"{base_q} ORDER BY timestamp LIMIT ?", [*params, limit]).fetchall()
    conn.close()

    events = [dict(r) for r in rows]
    cumulative = 0.0
    for i, ev in enumerate(events):
        ev["spin_number"]       = i + 1
        cumulative              = round(cumulative + (ev["win_amount"] or 0) - (ev["bet_amount"] or 0), 2)
        ev["cumulative_net"]    = cumulative

    return {"session_id": session_id, "event_count": len(events), "events": events}


@router.get("/summary")
def get_events_summary(session_id: int = Query(...)):
    """Aggregated event statistics — used by session detail KPIs."""
    conn = get_connection()
    row = conn.execute("""
        SELECT
            COUNT(*)                                    AS total_events,
            COUNT(CASE WHEN win_amount > 0 THEN 1 END) AS winning_spins,
            COUNT(CASE WHEN win_amount = 0 THEN 1 END) AS losing_spins,
            ROUND(AVG(bet_amount), 2)                  AS avg_bet,
            ROUND(MAX(win_amount), 2)                  AS biggest_win,
            ROUND(AVG(confidence_score), 3)            AS avg_confidence,
            COUNT(CASE WHEN confidence_score < 0.8 THEN 1 END) AS low_conf_count
        FROM events WHERE session_id=?
    """, (session_id,)).fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="Session not found.")
    d = dict(row)
    d["win_rate_pct"] = round((d["winning_spins"] or 0) / max(d["total_events"] or 1, 1) * 100, 1)
    return d


@router.get("/validate/{session_id}")
def validate_events(session_id: int):
    """Validate all events for a session and return flagged issues."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT id, session_id, timestamp, event_type, bet_amount, win_amount, balance_after, confidence_score "
        "FROM events WHERE session_id=? ORDER BY timestamp",
        (session_id,),
    ).fetchall()
    conn.close()

    events = [dict(r) for r in rows]
    result = validate_session_events(events)
    return {
        "session_id": session_id,
        "total_events": result.total_events,
        "valid_events": result.valid_events,
        "flagged_count": len(result.flagged),
        "auto_corrected": result.auto_corrected,
        "flagged": [
            {
                "event_id": f.event_id,
                "reason": f.reason,
                "severity": f.severity,
                "original_values": f.original_values,
                "suggested_values": f.suggested_values,
            }
            for f in result.flagged
        ],
    }

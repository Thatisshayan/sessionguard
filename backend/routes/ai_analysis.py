"""
backend/routes/ai_analysis.py
------------------------------
Claude AI analysis endpoints.

GET  /ai/status              — Is AI configured? What model? What cost?
POST /sessions/{id}/ai       — Run Claude analysis on a session
GET  /sessions/{id}/ai       — Get cached AI analysis (from insights table)

Maturity: Working Prototype
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from engines.ai_insights_engine import (
    analyse_session_with_ai,
    get_ai_status,
)
from database.db import get_connection

router = APIRouter(tags=["ai"])


@router.get("/ai/status")
def ai_status():
    """Return AI configuration status — used by Settings and SessionDetail."""
    return get_ai_status()


@router.post("/sessions/{session_id}/ai")
def run_ai_analysis(session_id: int):
    """
    Run Claude AI analysis on a session.
    Returns immediately with analysis result (synchronous for now).
    Falls back to rule-based if no API key configured.
    """
    conn = get_connection()
    s    = conn.execute("SELECT id FROM sessions WHERE id=?", (session_id,)).fetchone()
    conn.close()
    if not s:
        raise HTTPException(status_code=404, detail="Session not found.")
    return analyse_session_with_ai(session_id)


@router.get("/sessions/{session_id}/ai")
def get_ai_analysis(session_id: int):
    """
    Return the most recent AI insights for a session.
    If none exist yet, runs a fresh analysis.
    """
    conn     = get_connection()
    session  = conn.execute("SELECT id FROM sessions WHERE id=?", (session_id,)).fetchone()
    cached   = conn.execute(
        "SELECT text, severity FROM insights WHERE session_id=? AND text LIKE '[AI]%' ORDER BY id DESC LIMIT 5",
        (session_id,)
    ).fetchall()
    conn.close()

    if not session:
        raise HTTPException(status_code=404, detail="Session not found.")

    if cached:
        return {
            "session_id": session_id,
            "source":     "cached",
            "ai_available": get_ai_status()["available"],
            "insights":   [{"text": r["text"][4:], "severity": r["severity"]} for r in cached],
        }

    # No cache — run fresh
    return analyse_session_with_ai(session_id)

"""
backend/routes/ai_analysis.py
------------------------------
NVIDIA AI analysis endpoints.

GET  /ai/status              — Is AI configured? What model? What cost?
POST /sessions/{id}/ai       — Run NVIDIA AI analysis on a session
GET  /sessions/{id}/ai       — Get cached AI analysis (from insights table)
GET  /sessions/{id}/ai/stream — Stream AI analysis via Server-Sent Events

Maturity: Working Prototype
"""

import asyncio
import json
from fastapi import APIRouter, HTTPException, BackgroundTasks, Header
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from backend.auth.access import require_admin, require_current_user, require_session_access
from engines.ai_insights_engine import (
    analyse_session_with_ai,
    get_ai_status,
    set_model,
    stream_analyse_session,
    NVIDIA_MODELS,
)
from database.db import get_connection, async_fetch_one

router = APIRouter(tags=["ai"])


@router.get("/ai/status")
def ai_status(authorization: str | None = Header(None, alias="Authorization")):
    """Return AI configuration status — used by Settings and SessionDetail."""
    require_current_user(authorization)
    return get_ai_status()


class ModelSwitch(BaseModel):
    model: str

@router.post("/ai/model")
async def switch_model(body: ModelSwitch, authorization: str | None = Header(None, alias="Authorization")):
    """Switch the active NVIDIA AI model."""
    await require_admin(authorization)
    result = await asyncio.to_thread(set_model, body.model)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.get("/ai/models")
def list_models(authorization: str | None = Header(None, alias="Authorization")):
    """Return available NVIDIA models."""
    require_current_user(authorization)
    return {"models": NVIDIA_MODELS, "current": get_ai_status()["model"]}


@router.get("/ai/usage")
async def get_ai_usage_stats(authorization: str | None = Header(None, alias="Authorization")):
    """Return platform-wide AI token and compute cost usage metrics."""
    require_current_user(authorization)
    from database.db import async_fetch_one
    row = await async_fetch_one("""
        SELECT
            COUNT(*)                    AS total_calls,
            COALESCE(SUM(input_tokens), 0)  AS total_input_tokens,
            COALESCE(SUM(output_tokens), 0) AS total_output_tokens,
            COALESCE(SUM(cost_usd), 0.0)    AS total_cost_usd
        FROM ai_cost_log
    """)
    res = dict(row) if row else {"total_calls": 0, "total_input_tokens": 0, "total_output_tokens": 0, "total_cost_usd": 0.0}
    res["total_cost_usd"] = round(res["total_cost_usd"], 4)
    return res


@router.post("/sessions/{session_id}/ai")
async def run_ai_analysis(session_id: int, authorization: str | None = Header(None, alias="Authorization")):
    """
    Run NVIDIA AI analysis on a session.
    Returns immediately with analysis result (synchronous for now).
    Falls back to rule-based if no API key configured.
    """
    await require_session_access(session_id, authorization)
    s = await async_fetch_one("SELECT id FROM sessions WHERE id=?", (session_id,))
    if not s:
        raise HTTPException(status_code=404, detail="Session not found.")
    return await asyncio.to_thread(analyse_session_with_ai, session_id)


@router.get("/sessions/{session_id}/ai")
async def get_ai_analysis(session_id: int, authorization: str | None = Header(None, alias="Authorization")):
    """
    Return the most recent AI insights for a session.
    If none exist yet, runs a fresh analysis.
    """
    from database.db import async_fetch_all
    await require_session_access(session_id, authorization)
    session = await async_fetch_one("SELECT id FROM sessions WHERE id=?", (session_id,))
    cached = await async_fetch_all(
        "SELECT text, severity FROM insights WHERE session_id=? AND text LIKE '[AI]%' ORDER BY id DESC LIMIT 5",
        (session_id,)
    )

    if not session:
        raise HTTPException(status_code=404, detail="Session not found.")

    if cached:
        return {
            "session_id": session_id,
            "source":     "cached",
            "ai_available": (await asyncio.to_thread(get_ai_status))["available"],
            "insights":   [{"text": r["text"][4:], "severity": r["severity"]} for r in cached],
        }

    # No cache — run fresh
    return await asyncio.to_thread(analyse_session_with_ai, session_id)


@router.get("/sessions/{session_id}/ai/stream")
async def stream_ai_analysis(session_id: int, authorization: str | None = Header(None, alias="Authorization")):
    """
    Stream AI analysis for a session via Server-Sent Events.
    Frontend consumes this for real-time AI response display.
    """
    await require_session_access(session_id, authorization)
    session = await async_fetch_one("SELECT id FROM sessions WHERE id=?", (session_id,))
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found.")
    
    def event_generator():
        for event in stream_analyse_session(session_id):
            yield f"data: {json.dumps(event)}\n\n"
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )

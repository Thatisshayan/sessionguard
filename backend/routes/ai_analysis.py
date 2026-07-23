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
from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
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
def ai_status():
    """Return AI configuration status — used by Settings and SessionDetail."""
    return get_ai_status()


class ModelSwitch(BaseModel):
    model: str

@router.post("/ai/model")
def switch_model(body: ModelSwitch):
    """Switch the active NVIDIA AI model."""
    result = set_model(body.model)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.get("/ai/models")
def list_models():
    """Return available NVIDIA models."""
    return {"models": NVIDIA_MODELS, "current": get_ai_status()["model"]}


@router.post("/sessions/{session_id}/ai")
async def run_ai_analysis(session_id: int):
    """
    Run NVIDIA AI analysis on a session.
    Returns immediately with analysis result (synchronous for now).
    Falls back to rule-based if no API key configured.
    """
    s = await async_fetch_one("SELECT id FROM sessions WHERE id=?", (session_id,))
    if not s:
        raise HTTPException(status_code=404, detail="Session not found.")
    return await asyncio.to_thread(analyse_session_with_ai, session_id)


@router.get("/sessions/{session_id}/ai")
async def get_ai_analysis(session_id: int):
    """
    Return the most recent AI insights for a session.
    If none exist yet, runs a fresh analysis.
    """
    from database.db import async_fetch_all
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
async def stream_ai_analysis(session_id: int):
    """
    Stream AI analysis for a session via Server-Sent Events.
    Frontend consumes this for real-time AI response display.
    """
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

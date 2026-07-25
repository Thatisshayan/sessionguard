"""
backend/routes/insights.py
---------------------------
Insight retrieval and regeneration endpoints.
All routes wrap sync engine calls with asyncio.to_thread.
"""

import asyncio

from fastapi import APIRouter, HTTPException, Query, Header
from typing import Optional
from engines.insights_engine import get_insights, generate_and_persist_insights
from backend.auth.access import require_admin, require_session_access

router = APIRouter(tags=["insights"])


@router.get("")
async def list_insights(
    session_id: Optional[int] = Query(None),
    limit:      int           = Query(50, le=200),
    authorization: Optional[str] = Header(None, alias="Authorization"),
):
    """Return insights, optionally filtered by session. Critical first."""
    if session_id is not None:
        await require_session_access(session_id, authorization)
    else:
        await require_admin(authorization)
    return await asyncio.to_thread(get_insights, session_id=session_id, limit=limit)


@router.post("/{session_id}/regenerate")
async def regenerate_insights(session_id: int, authorization: Optional[str] = Header(None, alias="Authorization")):
    """Re-run insight rules for a session. Replaces existing insights."""
    await require_session_access(session_id, authorization)
    results = await asyncio.to_thread(generate_and_persist_insights, session_id)
    if results is None:
        raise HTTPException(status_code=404, detail="Session not found.")
    return {"session_id": session_id, "generated": len(results), "insights": results}

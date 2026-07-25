"""
backend/routes/trends.py
-------------------------
Phase 9 + 10 analytics endpoints.
Trend engine, session streaks, health scores, drift projection,
early warnings, pattern memory.

Maturity: Working Prototype
"""

import asyncio
from fastapi import APIRouter, HTTPException, Query, Header
from engines.trend_engine import (
    get_rolling_trends,
    get_session_streaks,
    get_session_health,
    project_session_drift,
    get_early_warnings,
    get_pattern_memory,
)
from backend.auth.access import require_admin, require_session_access

router = APIRouter(tags=["trends"])


@router.get("/trends/rolling")
async def rolling_trends(last_n: int = Query(10, ge=3, le=50), authorization: str | None = Header(None, alias="Authorization")):
    """Rolling RTP + net trends across last N sessions."""
    await require_admin(authorization)
    return await asyncio.to_thread(get_rolling_trends, last_n)


@router.get("/trends/streaks")
async def session_streaks(authorization: str | None = Header(None, alias="Authorization")):
    """Winning/losing session streak analysis."""
    await require_admin(authorization)
    return await asyncio.to_thread(get_session_streaks)


@router.get("/trends/pattern-memory")
async def pattern_memory(last_n: int = Query(20, ge=6, le=100), authorization: str | None = Header(None, alias="Authorization")):
    """Cross-session behaviour change tracking — early vs recent sessions."""
    await require_admin(authorization)
    return await asyncio.to_thread(get_pattern_memory, last_n)


@router.get("/sessions/{session_id}/health")
async def session_health(session_id: int, authorization: str | None = Header(None, alias="Authorization")):
    """Composite health score (0-100) for a session."""
    await require_session_access(session_id, authorization)
    r = await asyncio.to_thread(get_session_health, session_id)
    if "error" in r:
        raise HTTPException(status_code=404, detail=r["error"])
    return r


@router.get("/sessions/{session_id}/drift")
async def session_drift(
    session_id: int,
    project_n: int = Query(20, ge=5, le=100),
    authorization: str | None = Header(None, alias="Authorization"),
):
    """
    Balance trajectory projection for a session.
    Based on observed trend — not an outcome prediction.
    """
    await require_session_access(session_id, authorization)
    r = await asyncio.to_thread(project_session_drift, session_id, project_n)
    if r.get("status") == "insufficient_data":
        raise HTTPException(
            status_code=422,
            detail=f"Need at least {r['need']} events — have {r['have']}."
        )
    return r


@router.get("/sessions/{session_id}/warnings")
async def early_warnings(session_id: int, authorization: str | None = Header(None, alias="Authorization")):
    """Early warning heuristics — fires before formal alerts."""
    await require_session_access(session_id, authorization)
    return await asyncio.to_thread(get_early_warnings, session_id)

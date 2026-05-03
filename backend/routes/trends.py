"""
backend/routes/trends.py
-------------------------
Phase 9 + 10 analytics endpoints.
Trend engine, session streaks, health scores, drift projection,
early warnings, pattern memory.

Maturity: Working Prototype
"""

from fastapi import APIRouter, HTTPException, Query
from engines.trend_engine import (
    get_rolling_trends,
    get_session_streaks,
    get_session_health,
    project_session_drift,
    get_early_warnings,
    get_pattern_memory,
)

router = APIRouter(tags=["trends"])


@router.get("/trends/rolling")
def rolling_trends(last_n: int = Query(10, ge=3, le=50)):
    """Rolling RTP + net trends across last N sessions."""
    return get_rolling_trends(last_n)


@router.get("/trends/streaks")
def session_streaks():
    """Winning/losing session streak analysis."""
    return get_session_streaks()


@router.get("/trends/pattern-memory")
def pattern_memory(last_n: int = Query(20, ge=6, le=100)):
    """Cross-session behaviour change tracking — early vs recent sessions."""
    return get_pattern_memory(last_n)


@router.get("/sessions/{session_id}/health")
def session_health(session_id: int):
    """Composite health score (0-100) for a session."""
    r = get_session_health(session_id)
    if "error" in r:
        raise HTTPException(status_code=404, detail=r["error"])
    return r


@router.get("/sessions/{session_id}/drift")
def session_drift(
    session_id: int,
    project_n: int = Query(20, ge=5, le=100),
):
    """
    Balance trajectory projection for a session.
    Based on observed trend — not an outcome prediction.
    """
    r = project_session_drift(session_id, project_n)
    if r.get("status") == "insufficient_data":
        raise HTTPException(
            status_code=422,
            detail=f"Need at least {r['need']} events — have {r['have']}."
        )
    return r


@router.get("/sessions/{session_id}/warnings")
def early_warnings(session_id: int):
    """Early warning heuristics — fires before formal alerts."""
    return get_early_warnings(session_id)

"""
backend/routes/insights.py
---------------------------
Insight retrieval and regeneration endpoints.
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from engines.insights_engine import get_insights, generate_and_persist_insights

router = APIRouter(tags=["insights"])


@router.get("")
def list_insights(
    session_id: Optional[int] = Query(None),
    limit:      int           = Query(50, le=200),
):
    """Return insights, optionally filtered by session. Critical first."""
    return get_insights(session_id=session_id, limit=limit)


@router.post("/{session_id}/regenerate")
def regenerate_insights(session_id: int):
    """Re-run insight rules for a session. Replaces existing insights."""
    results = generate_and_persist_insights(session_id)
    if results is None:
        raise HTTPException(status_code=404, detail="Session not found.")
    return {"session_id": session_id, "generated": len(results), "insights": results}

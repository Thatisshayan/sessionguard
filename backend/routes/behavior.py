"""
backend/routes/behavior.py
---------------------------
Behavior pattern analysis endpoints.
Maturity: Working Prototype
"""

from fastapi import APIRouter, HTTPException
from engines.behavior_engine import analyze_behavior, analyze_behavior_global

router = APIRouter(tags=["behavior"])


@router.get("/session/{session_id}")
def session_behavior(session_id: int):
    """Run all behavior detectors for a single session."""
    result = analyze_behavior(session_id)
    if result.get("status") == "insufficient_data":
        raise HTTPException(status_code=422, detail=result["message"])
    return result


@router.get("/global")
def global_behavior():
    """Cross-session behavior summary — top risk sessions."""
    return analyze_behavior_global()

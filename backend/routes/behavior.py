"""
backend/routes/behavior.py
---------------------------
Behavior pattern analysis endpoints.
Maturity: Working Prototype
"""

from fastapi import APIRouter, HTTPException, Header
from typing import Optional
from backend.auth.access import require_admin, require_session_access
from engines.behavior_engine import analyze_behavior, analyze_behavior_global

router = APIRouter(tags=["behavior"])


@router.get("/session/{session_id}")
async def session_behavior(session_id: int, authorization: Optional[str] = Header(None, alias="Authorization")):
    """Run all behavior detectors for a single session."""
    await require_session_access(session_id, authorization)
    result = analyze_behavior(session_id)
    if result.get("status") == "insufficient_data":
        raise HTTPException(status_code=422, detail=result["message"])
    return result


@router.get("/global")
def global_behavior(authorization: Optional[str] = Header(None, alias="Authorization")):
    """Cross-session behavior summary — top risk sessions."""
    require_admin(authorization)
    return analyze_behavior_global()

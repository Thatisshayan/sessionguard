"""
backend/routes/compare.py
--------------------------
Session comparison endpoint.
"""

from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel
from typing import Optional
from backend.auth.access import require_current_user, require_session_access
from engines.comparison_engine import compare_sessions

router = APIRouter(tags=["compare"])


class CompareRequest(BaseModel):
    session_ids: list[int]


@router.post("")
async def run_comparison(
    body: CompareRequest,
    authorization: Optional[str] = Header(None, alias="Authorization"),
):
    """Compare two or more sessions. Returns metrics diff + narrative."""
    if len(body.session_ids) < 2:
        raise HTTPException(status_code=400, detail="Provide at least 2 session IDs.")
    require_current_user(authorization)
    for session_id in body.session_ids:
        await require_session_access(session_id, authorization)
    return compare_sessions(body.session_ids)

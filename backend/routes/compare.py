"""
backend/routes/compare.py
--------------------------
Session comparison endpoint.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from engines.comparison_engine import compare_sessions

router = APIRouter(tags=["compare"])


class CompareRequest(BaseModel):
    session_ids: list[int]


@router.post("")
def run_comparison(body: CompareRequest):
    """Compare two or more sessions. Returns metrics diff + narrative."""
    if len(body.session_ids) < 2:
        raise HTTPException(status_code=400, detail="Provide at least 2 session IDs.")
    return compare_sessions(body.session_ids)

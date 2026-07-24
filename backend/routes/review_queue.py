"""
backend/routes/review_queue.py
-------------------------------
Review queue retrieval and resolution endpoints.
Uncertain-first ordering per roadmap spec.
"""

from fastapi import APIRouter, HTTPException, Query, Header
from pydantic import BaseModel
from typing import Optional
from database.db import get_connection
from backend.auth.access import require_admin, require_session_access
from engines.review_queue_engine import (
    get_review_queue,
    resolve_review_item,
    get_queue_summary,
)

router = APIRouter(tags=["review-queue"])


class ResolveAction(BaseModel):
    action:           str            # accepted | rejected | corrected
    corrected_value:  Optional[str] = ""


@router.get("")
async def list_review_items(
    authorization: Optional[str] = Header(None, alias="Authorization"),
    session_id: Optional[int] = Query(None),
    status:     Optional[str] = Query("pending"),
):
    """Return review items sorted by lowest confidence first."""
    if session_id is not None:
        await require_session_access(session_id, authorization)
    else:
        require_admin(authorization)
    return get_review_queue(session_id=session_id, status=status)


@router.get("/summary")
def queue_summary(authorization: Optional[str] = Header(None, alias="Authorization")):
    """Return pending/total counts for dashboard badge."""
    require_admin(authorization)
    return get_queue_summary()


@router.patch("/{item_id}/resolve")
async def resolve_item(
    item_id: int,
    body: ResolveAction,
    authorization: Optional[str] = Header(None, alias="Authorization"),
):
    """Accept, reject, or mark a review item as corrected."""
    conn = get_connection()
    row = conn.execute("SELECT session_id FROM review_items WHERE id=?", (item_id,)).fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail=f"Review item {item_id} not found.")

    await require_session_access(row["session_id"], authorization)

    success = resolve_review_item(
        item_id=item_id,
        action=body.action,
        corrected_value=body.corrected_value or "",
    )
    if not success:
        raise HTTPException(
            status_code=404,
            detail=f"Review item {item_id} not found or invalid action '{body.action}'."
        )
    return {"item_id": item_id, "status": body.action}

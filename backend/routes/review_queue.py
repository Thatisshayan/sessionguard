"""
backend/routes/review_queue.py
-------------------------------
Review queue retrieval and resolution endpoints.
Uncertain-first ordering per roadmap spec.
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional
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
def list_review_items(
    session_id: Optional[int] = Query(None),
    status:     Optional[str] = Query("pending"),
):
    """Return review items sorted by lowest confidence first."""
    return get_review_queue(session_id=session_id, status=status)


@router.get("/summary")
def queue_summary():
    """Return pending/total counts for dashboard badge."""
    return get_queue_summary()


@router.patch("/{item_id}/resolve")
def resolve_item(item_id: int, body: ResolveAction):
    """Accept, reject, or mark a review item as corrected."""
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

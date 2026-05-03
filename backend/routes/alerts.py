"""
backend/routes/alerts.py
-------------------------
Alert retrieval, acknowledgement, and summary endpoints.
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from engines.alerts_engine import (
    get_alerts,
    acknowledge_alert,
    generate_and_persist_alerts,
    get_alert_summary,
)

router = APIRouter(tags=["alerts"])


@router.get("")
def list_alerts(
    session_id:          Optional[int]  = Query(None),
    unacknowledged_only: bool           = Query(False),
):
    """Return alerts. Critical first. Optionally filter by session or status."""
    return get_alerts(session_id=session_id, unacknowledged_only=unacknowledged_only)


@router.get("/summary")
def alert_summary():
    """Return counts by severity for dashboard badges."""
    return get_alert_summary()


@router.patch("/{alert_id}/acknowledge")
def acknowledge(alert_id: int):
    """Mark an alert as acknowledged."""
    success = acknowledge_alert(alert_id)
    if not success:
        raise HTTPException(status_code=404, detail="Alert not found.")
    return {"alert_id": alert_id, "acknowledged": True}


@router.post("/{session_id}/regenerate")
def regenerate_alerts(session_id: int):
    """Re-run alert rules for a session. Replaces existing alerts."""
    results = generate_and_persist_alerts(session_id)
    if results is None:
        raise HTTPException(status_code=404, detail="Session not found.")
    return {"session_id": session_id, "generated": len(results), "alerts": results}

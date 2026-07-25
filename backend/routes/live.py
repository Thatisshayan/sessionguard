"""
backend/routes/live.py
-----------------------
Live session monitoring endpoints.
Maturity: Working Prototype — mock mode fully working, screen mode wired.
"""

from fastapi import APIRouter, HTTPException, Query, Header
from pydantic import BaseModel
from typing import Optional
from backend.auth.access import require_admin, require_session_access
from database.db import get_connection
from engines.live_engine import (
    start_live_run, pause_live_run, resume_live_run, stop_live_run,
    get_live_run, get_live_events, get_session_live_runs,
)

router = APIRouter(tags=["live"])


class StartRunRequest(BaseModel):
    session_id:       int
    mode:             str   = "mock"      # mock | screen
    tick_interval:    float = 2.0
    autosave_enabled: bool  = True
    roi_config:       Optional[dict] = None


@router.post("/start")
async def start_run(
    body: StartRunRequest,
    authorization: Optional[str] = Header(None, alias="Authorization"),
):
    """Start a live monitoring run for a session."""
    await require_session_access(body.session_id, authorization)
    result = start_live_run(
        session_id=body.session_id,
        mode=body.mode,
        tick_interval=body.tick_interval,
        autosave_enabled=body.autosave_enabled,
        roi_config=body.roi_config,
    )
    if not result["success"]:
        raise HTTPException(status_code=409, detail=result["error"])
    return result


@router.post("/{run_id}/pause")
async def pause_run(run_id: int, authorization: Optional[str] = Header(None, alias="Authorization")):
    run = get_live_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found.")
    await require_session_access(run["session_id"], authorization)
    result = pause_live_run(run_id)
    if not result["success"]:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@router.post("/{run_id}/resume")
async def resume_run(run_id: int, authorization: Optional[str] = Header(None, alias="Authorization")):
    run = get_live_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found.")
    await require_session_access(run["session_id"], authorization)
    result = resume_live_run(run_id)
    if not result["success"]:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@router.post("/{run_id}/stop")
async def stop_run(run_id: int, authorization: Optional[str] = Header(None, alias="Authorization")):
    run = get_live_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found.")
    await require_session_access(run["session_id"], authorization)
    return stop_live_run(run_id)


@router.get("/{run_id}")
async def get_run(run_id: int, authorization: Optional[str] = Header(None, alias="Authorization")):
    run = get_live_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found.")
    await require_session_access(run["session_id"], authorization)
    return run


@router.get("/{run_id}/events")
async def get_run_events(
    run_id: int,
    authorization: Optional[str] = Header(None, alias="Authorization"),
    since_id: int = Query(0),
    limit:    int = Query(50, le=200),
):
    """Poll for new events since a given event ID. Used for live feed UI."""
    run = get_live_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found.")
    await require_session_access(run["session_id"], authorization)
    return get_live_events(run_id=run_id, since_id=since_id, limit=limit)


@router.get("/session/{session_id}/runs")
async def session_runs(session_id: int, authorization: Optional[str] = Header(None, alias="Authorization")):
    """Return all live runs for a session."""
    await require_session_access(session_id, authorization)
    return get_session_live_runs(session_id)

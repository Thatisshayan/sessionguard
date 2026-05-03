"""
backend/routes/live.py
-----------------------
Live session monitoring endpoints.
Maturity: Working Prototype — mock mode fully working, screen mode wired.
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional
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
def start_run(body: StartRunRequest):
    """Start a live monitoring run for a session."""
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
def pause_run(run_id: int):
    result = pause_live_run(run_id)
    if not result["success"]:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@router.post("/{run_id}/resume")
def resume_run(run_id: int):
    result = resume_live_run(run_id)
    if not result["success"]:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@router.post("/{run_id}/stop")
def stop_run(run_id: int):
    return stop_live_run(run_id)


@router.get("/{run_id}")
def get_run(run_id: int):
    run = get_live_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found.")
    return run


@router.get("/{run_id}/events")
def get_run_events(
    run_id: int,
    since_id: int = Query(0),
    limit:    int = Query(50, le=200),
):
    """Poll for new events since a given event ID. Used for live feed UI."""
    return get_live_events(run_id=run_id, since_id=since_id, limit=limit)


@router.get("/session/{session_id}/runs")
def session_runs(session_id: int):
    """Return all live runs for a session."""
    return get_session_live_runs(session_id)

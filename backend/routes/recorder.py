"""
backend/routes/recorder.py
---------------------------
Screen recorder control endpoints.
Frontend → API → desktop_app/recorder/ffmpeg_runner.py → FFmpeg process.

Maturity: Working Prototype
"""

from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel
from typing import Optional
from backend.auth.access import require_admin

router = APIRouter(tags=["recorder"])


class StartRequest(BaseModel):
    session_id: Optional[int] = None
    fps:        int            = 30
    region:     Optional[list[int]] = None  # [x, y, w, h]


@router.post("/recorder/start")
def start(body: StartRequest, authorization: Optional[str] = Header(None, alias="Authorization")):
    require_admin(authorization)
    from desktop_app.recorder.ffmpeg_runner import start_recording
    region = tuple(body.region) if body.region and len(body.region) == 4 else None
    result = start_recording(
        session_id=body.session_id,
        fps=body.fps,
        region=region,
    )
    if not result["success"]:
        raise HTTPException(status_code=409, detail=result["error"])
    return result


@router.post("/recorder/stop")
def stop(authorization: Optional[str] = Header(None, alias="Authorization")):
    require_admin(authorization)
    from desktop_app.recorder.ffmpeg_runner import stop_recording
    result = stop_recording()
    if not result["success"]:
        raise HTTPException(status_code=409, detail=result["error"])
    return result


@router.get("/recorder/status")
def status(authorization: Optional[str] = Header(None, alias="Authorization")):
    require_admin(authorization)
    from desktop_app.recorder.ffmpeg_runner import get_recording_status
    return get_recording_status()


@router.get("/recorder/list")
def recordings(authorization: Optional[str] = Header(None, alias="Authorization")):
    require_admin(authorization)
    from desktop_app.recorder.ffmpeg_runner import list_recordings
    return list_recordings()

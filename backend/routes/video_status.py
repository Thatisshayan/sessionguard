"""
backend/routes/video_status.py — FFmpeg pipeline readiness check.
"""

from fastapi import APIRouter, Header
from typing import Optional
from backend.auth.access import require_admin
from engines.video_pipeline import check_ffmpeg

router = APIRouter(tags=["video"])

@router.get("")
def video_status(authorization: Optional[str] = Header(None, alias="Authorization")):
    """Check FFmpeg availability and version."""
    require_admin(authorization)
    return check_ffmpeg()

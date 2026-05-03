"""
backend/routes/video_status.py — FFmpeg pipeline readiness check.
"""

from fastapi import APIRouter
from engines.video_pipeline import check_ffmpeg

router = APIRouter(tags=["video"])

@router.get("")
def video_status():
    """Check FFmpeg availability and version."""
    return check_ffmpeg()

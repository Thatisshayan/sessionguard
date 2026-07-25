"""
backend/routes/video_status.py — FFmpeg pipeline readiness check.
"""

import asyncio
from fastapi import APIRouter, Header
from typing import Optional
from backend.auth.access import require_admin
from engines.video_pipeline import check_ffmpeg

router = APIRouter(tags=["video"])

@router.get("")
async def video_status(authorization: Optional[str] = Header(None, alias="Authorization")):
    """Check FFmpeg availability and version."""
    await require_admin(authorization)
    return await asyncio.to_thread(check_ffmpeg)

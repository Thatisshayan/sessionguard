"""
backend/routes/ocr_status.py — OCR backend availability check.
"""

import asyncio
from fastapi import APIRouter
from engines.ocr_engine import check_ocr_status

router = APIRouter(tags=["ocr"])

@router.get("")
async def ocr_status():
    """Check which OCR backends are installed and available."""
    return await asyncio.to_thread(check_ocr_status)

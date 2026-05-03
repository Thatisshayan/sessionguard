"""
backend/routes/ocr_status.py — OCR backend availability check.
"""

from fastapi import APIRouter
from engines.ocr_engine import check_ocr_status

router = APIRouter(tags=["ocr"])

@router.get("")
def ocr_status():
    """Check which OCR backends are installed and available."""
    return check_ocr_status()

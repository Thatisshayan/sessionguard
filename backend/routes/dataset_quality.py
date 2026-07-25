"""
backend/routes/dataset_quality.py
----------------------------------
Dataset quality report endpoint.
"""

from fastapi import APIRouter, Header
from typing import Optional
from backend.auth.access import require_admin
from engines.dataset_quality import get_dataset_quality

router = APIRouter(tags=["dataset-quality"])


@router.get("")
def dataset_quality(authorization: Optional[str] = Header(None, alias="Authorization")):
    """Return dataset quality metrics for compliance/self-audit."""
    require_admin(authorization)
    return get_dataset_quality()

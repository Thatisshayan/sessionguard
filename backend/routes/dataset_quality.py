"""
backend/routes/dataset_quality.py
----------------------------------
Dataset quality report endpoint.
"""

from fastapi import APIRouter
from engines.dataset_quality import get_dataset_quality

router = APIRouter(tags=["dataset-quality"])


@router.get("")
def dataset_quality():
    """Return dataset quality metrics for compliance/self-audit."""
    return get_dataset_quality()

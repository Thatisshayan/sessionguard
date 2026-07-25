"""
backend/routes/parser_benchmark.py
------------------------------------
Parser benchmark endpoints.
Maturity: Working Prototype
"""

from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Header
from pydantic import BaseModel
from typing import Optional
import shutil
import tempfile
from pathlib import Path
from backend.auth.access import require_admin
from engines.parser_benchmark import run_benchmark, benchmark_profile

router = APIRouter(tags=["parser-benchmark"])


class BenchmarkRequest(BaseModel):
    frame_paths:  list[str]
    roi_config:   Optional[dict]       = None
    ground_truth: Optional[list[dict]] = None
    profile_id:   Optional[int]        = None


@router.post("")
def run_parser_benchmark(
    body: BenchmarkRequest,
    authorization: Optional[str] = Header(None, alias="Authorization"),
):
    """
    Run OCR accuracy benchmark over a set of frames.
    Can use inline roi_config or load from a stored profile.
    """
    require_admin(authorization)
    if not body.frame_paths:
        raise HTTPException(status_code=400, detail="Provide at least one frame_path.")

    if body.profile_id:
        result = benchmark_profile(body.profile_id, body.frame_paths)
    else:
        result = run_benchmark(
            frame_paths=body.frame_paths,
            roi_config=body.roi_config,
            ground_truth=body.ground_truth,
        )

    return result


@router.post("/upload-frame")
async def benchmark_uploaded_frame(
    file: UploadFile = File(...),
    roi_config: str  = Form("{}"),
    authorization: Optional[str] = Header(None, alias="Authorization"),
):
    """
    Upload a single frame image and run OCR benchmark on it.
    Returns field extraction results with confidence scores.
    """
    require_admin(authorization)
    import json
    try:
        roi = json.loads(roi_config)
    except Exception:
        roi = {}

    suffix = Path(file.filename or "frame.png").suffix or ".png"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = tmp.name

    try:
        result = run_benchmark([tmp_path], roi_config=roi or None)
    finally:
        Path(tmp_path).unlink(missing_ok=True)

    return result

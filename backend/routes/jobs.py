"""
backend/routes/jobs.py
-----------------------
Job queue management endpoints.
Maturity: Working Prototype — enhanced with thread-pool worker health
"""

import asyncio
import json
from pathlib import Path
from fastapi import APIRouter, HTTPException, Header, Query
from pydantic import BaseModel
from typing import Optional
from backend.workers.job_service import (
    enqueue_job, get_job, list_jobs, cancel_job,
    get_worker_health, cleanup_completed_jobs, cleanup_video_frames
)
from backend.auth.service import get_current_user_from_token

router = APIRouter(tags=["jobs"])


class JobRequest(BaseModel):
    job_type:   str
    session_id: Optional[int]  = None
    upload_id:  Optional[int]  = None
    payload:    Optional[dict] = None


@router.post("", status_code=202)
async def submit_job(body: JobRequest, authorization: str = Header(...)):
    """Submit a background job. Returns immediately with job_id."""
    user = await asyncio.to_thread(get_current_user_from_token, authorization)
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required.")
    user_id = user["user_id"]

    valid_types = {"video_pipeline", "csv_parse", "export_pdf", "export_excel", "regenerate"}
    if body.job_type not in valid_types:
        raise HTTPException(status_code=400, detail=f"Unknown job type. Valid: {valid_types}")

    result = await asyncio.to_thread(
        enqueue_job,
        job_type=body.job_type,
        session_id=body.session_id,
        upload_id=body.upload_id,
        user_id=user_id,
        payload=body.payload,
    )
    return result


@router.get("/{job_id}")
async def poll_job(job_id: int, authorization: Optional[str] = Header(None)):
    """Poll job status and progress. Call repeatedly until status=complete."""
    user = await asyncio.to_thread(get_current_user_from_token, authorization)
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required.")

    job = await asyncio.to_thread(get_job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")

    if user["role"] != "admin" and job.get("user_id") is not None and job.get("user_id") != user["user_id"]:
        raise HTTPException(status_code=403, detail="Access denied to job.")

    return job


@router.post("/{job_id}/cancel")
async def cancel(job_id: int, authorization: str = Header(...)):
    """Cancel a pending or running job."""
    user = await asyncio.to_thread(get_current_user_from_token, authorization)
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required.")

    job = await asyncio.to_thread(get_job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")

    if user["role"] != "admin" and job.get("user_id") is not None and job.get("user_id") != user["user_id"]:
        raise HTTPException(status_code=403, detail="Access denied to job.")

    success = await asyncio.to_thread(cancel_job, job_id)
    if not success:
        raise HTTPException(status_code=409, detail="Job cannot be cancelled (running or already done).")
    return {"job_id": job_id, "status": "cancelled"}


@router.get("")
async def list_jobs_endpoint(
    status:     Optional[str] = Query(None),
    session_id: Optional[int] = Query(None),
    limit:      int           = Query(50, le=200),
    authorization: Optional[str] = Header(None),
):
    """List jobs — filter by status or session."""
    user = await asyncio.to_thread(get_current_user_from_token, authorization)
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required.")

    user_id = None if user["role"] == "admin" else user["user_id"]
    return await asyncio.to_thread(
        list_jobs,
        status=status,
        session_id=session_id,
        user_id=user_id,
        limit=limit,
    )


@router.get("/worker/health")
async def worker_health():
    """Worker pool health: active/pending jobs, capacity."""
    return await asyncio.to_thread(get_worker_health)


_CONFIG_PATH = Path(__file__).resolve().parent.parent.parent / "config" / "app_config.json"


def _frame_retention_hours(default: int = 24) -> int:
    """Read frame cleanup retention from app_config.json, falling back to default."""
    try:
        cfg = json.loads(_CONFIG_PATH.read_text(encoding="utf-8"))
        value = cfg.get("storage", {}).get("frame_cleanup_retention_hours", default)
        return int(value)
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        return default


@router.post("/worker/cleanup")
async def cleanup_worker(
    max_age_seconds: int = 3600,
    retention_hours: Optional[int] = None,
    authorization: Optional[str] = Header(None),
):
    """Clean up completed job metadata and video frame directories. Admin only."""
    user = await asyncio.to_thread(get_current_user_from_token, authorization)
    if not user or user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin access required.")

    if retention_hours is None:
        retention_hours = await asyncio.to_thread(_frame_retention_hours)

    removed = await asyncio.to_thread(cleanup_completed_jobs, max_age_seconds)
    frames = await asyncio.to_thread(cleanup_video_frames, retention_hours)
    return {
        "removed": removed,
        "max_age_seconds": max_age_seconds,
        "frames": frames,
    }

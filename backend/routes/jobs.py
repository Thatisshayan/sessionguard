"""
backend/routes/jobs.py
-----------------------
Job queue management endpoints.
Maturity: Working Prototype — enhanced with thread-pool worker health
"""

from fastapi import APIRouter, HTTPException, Header, Query
from pydantic import BaseModel
from typing import Optional
from backend.workers.job_service import (
    enqueue_job, get_job, list_jobs, cancel_job,
    get_worker_health, cleanup_completed_jobs
)
from backend.auth.service import get_current_user_from_token

router = APIRouter(tags=["jobs"])


class JobRequest(BaseModel):
    job_type:   str
    session_id: Optional[int]  = None
    upload_id:  Optional[int]  = None
    payload:    Optional[dict] = None


@router.post("", status_code=202)
def submit_job(body: JobRequest, authorization: str = Header(...)):
    """Submit a background job. Returns immediately with job_id."""
    user    = get_current_user_from_token(authorization)
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required.")
    user_id = user["user_id"]

    valid_types = {"video_pipeline", "csv_parse", "export_pdf", "export_excel", "regenerate"}
    if body.job_type not in valid_types:
        raise HTTPException(status_code=400, detail=f"Unknown job type. Valid: {valid_types}")

    result = enqueue_job(
        job_type=body.job_type,
        session_id=body.session_id,
        upload_id=body.upload_id,
        user_id=user_id,
        payload=body.payload,
    )
    return result


@router.get("/{job_id}")
def poll_job(job_id: int, authorization: Optional[str] = Header(None)):
    """Poll job status and progress. Call repeatedly until status=complete."""
    user = get_current_user_from_token(authorization)
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required.")

    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")
    
    if user["role"] != "admin" and job.get("user_id") is not None and job.get("user_id") != user["user_id"]:
        raise HTTPException(status_code=403, detail="Access denied to job.")
        
    return job


@router.post("/{job_id}/cancel")
def cancel(job_id: int, authorization: str = Header(...)):
    """Cancel a pending or running job."""
    user = get_current_user_from_token(authorization)
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required.")
    
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")

    if user["role"] != "admin" and job.get("user_id") is not None and job.get("user_id") != user["user_id"]:
        raise HTTPException(status_code=403, detail="Access denied to job.")
    
    success = cancel_job(job_id)
    if not success:
        raise HTTPException(status_code=409, detail="Job cannot be cancelled (running or already done).")
    return {"job_id": job_id, "status": "cancelled"}


@router.get("")
def list_jobs_endpoint(
    status:     Optional[str] = Query(None),
    session_id: Optional[int] = Query(None),
    limit:      int           = Query(50, le=200),
    authorization: Optional[str] = Header(None),
):
    """List jobs — filter by status or session."""
    user = get_current_user_from_token(authorization)
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required.")
    
    user_id = None if user["role"] == "admin" else user["user_id"]
    return list_jobs(status=status, session_id=session_id, user_id=user_id, limit=limit)


@router.get("/worker/health")
def worker_health():
    """Worker pool health: active/pending jobs, capacity."""
    return get_worker_health()


@router.post("/worker/cleanup")
def cleanup_worker(max_age_seconds: int = 3600):
    """Clean up completed job metadata older than max_age_seconds."""
    removed = cleanup_completed_jobs(max_age_seconds)
    return {"removed": removed, "max_age_seconds": max_age_seconds}

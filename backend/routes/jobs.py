"""
backend/routes/jobs.py
-----------------------
Job queue management endpoints.
Maturity: Working Prototype
"""

from fastapi import APIRouter, HTTPException, Header, Query
from pydantic import BaseModel
from typing import Optional
from backend.workers.job_service import enqueue_job, get_job, list_jobs, cancel_job
from backend.auth.service import get_current_user_from_token

router = APIRouter(tags=["jobs"])


class JobRequest(BaseModel):
    job_type:   str
    session_id: Optional[int]  = None
    upload_id:  Optional[int]  = None
    payload:    Optional[dict] = None


@router.post("", status_code=202)
def submit_job(body: JobRequest, authorization: Optional[str] = Header(None)):
    """Submit a background job. Returns immediately with job_id."""
    user    = get_current_user_from_token(authorization)
    user_id = user["user_id"] if user else None

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
def poll_job(job_id: int):
    """Poll job status and progress. Call repeatedly until status=complete."""
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")
    return job


@router.post("/{job_id}/cancel")
def cancel(job_id: int, authorization: Optional[str] = Header(None)):
    """Cancel a pending job."""
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
    user    = get_current_user_from_token(authorization)
    user_id = user["user_id"] if user else None
    return list_jobs(status=status, session_id=session_id, user_id=user_id, limit=limit)

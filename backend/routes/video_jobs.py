"""
backend/routes/video_jobs.py
-----------------------------
Video job debug endpoints — annotated frame export.
"""

import io
import zipfile
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from database.db import get_connection, async_fetch_one, async_fetch_all
from engines.frame_annotator import annotate_frame, create_annotated_zip
from engines.video_pipeline import get_video_job

router = APIRouter(tags=["video-jobs"])


@router.get("/{job_id}")
def get_job(job_id: int):
    """
    Return video job details including chunking progress fields.
    """
    job = get_video_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Video job not found.")
    return {
        "id":                job.get("id"),
        "session_id":        job.get("session_id"),
        "upload_id":         job.get("upload_id"),
        "status":            job.get("status"),
        "frames_extracted":  job.get("frames_extracted", 0),
        "frames_ocr_done":   job.get("frames_ocr_done", 0),
        "scene_changes":     job.get("scene_changes", 0),
        "events_built":      job.get("events_built", 0),
        "current_chunk":     job.get("current_chunk", 0),
        "total_chunks":      job.get("total_chunks", 0),
        "chunk_size_seconds": job.get("chunk_size_seconds", 300),
        "error_message":    job.get("error_message", ""),
        "started_at":        job.get("started_at", ""),
        "completed_at":     job.get("completed_at", ""),
        "output_dir":        job.get("output_dir", ""),
        "created_at":        job.get("created_at", ""),
    }


@router.get("/{job_id}/annotated-frames")
async def get_annotated_frames(job_id: int):
    """
    Download annotated frames for a video job as a ZIP.
    Each frame has ROI boxes and OCR text overlay.
    """
    job_row = await async_fetch_one("SELECT * FROM video_jobs WHERE id=?", (job_id,))
    if not job_row:
        raise HTTPException(status_code=404, detail="Video job not found.")

    job = dict(job_row)
    output_dir = job.get("output_dir")
    if not output_dir:
        raise HTTPException(status_code=404, detail="No output directory for this job.")

    session_id = job.get("session_id")
    ocr_rows = await async_fetch_all(
        "SELECT frame_path, balance_value, bet_value, win_value, confidence_bal, confidence_bet, confidence_win "
        "FROM ocr_results WHERE session_id=? ORDER BY id",
        (session_id,),
    )

    frames_data = []
    for row in ocr_rows:
        row = dict(row)
        frame_path = row.get("frame_path", "")
        if not frame_path:
            continue
        ocr_data = {}
        if row.get("balance_value") is not None:
            ocr_data["balance"] = {"value": row["balance_value"], "confidence": row.get("confidence_bal", 0), "bbox": None}
        if row.get("bet_value") is not None:
            ocr_data["bet"] = {"value": row["bet_value"], "confidence": row.get("confidence_bet", 0), "bbox": None}
        if row.get("win_value") is not None:
            ocr_data["win"] = {"value": row["win_value"], "confidence": row.get("confidence_win", 0), "bbox": None}
        frames_data.append({"frame_path": frame_path, "ocr_data": ocr_data})

    if not frames_data:
        raise HTTPException(status_code=404, detail="No frames found for this job.")

    zip_bytes = create_annotated_zip(frames_data)
    return StreamingResponse(
        io.BytesIO(zip_bytes),
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename=annotated-frames-job-{job_id}.zip"},
    )

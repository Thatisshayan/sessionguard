"""
backend/routes/video_jobs.py
-----------------------------
Video job debug endpoints — annotated frame export.
"""

import io
import zipfile
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from database.db import get_connection
from engines.frame_annotator import annotate_frame, create_annotated_zip

router = APIRouter(tags=["video-jobs"])


@router.get("/{job_id}/annotated-frames")
def get_annotated_frames(job_id: int):
    """
    Download annotated frames for a video job as a ZIP.
    Each frame has ROI boxes and OCR text overlay.
    """
    conn = get_connection()
    job = conn.execute("SELECT * FROM video_jobs WHERE id=?", (job_id,)).fetchone()
    if not job:
        conn.close()
        raise HTTPException(status_code=404, detail="Video job not found.")

    job = dict(job)
    output_dir = job.get("output_dir")
    if not output_dir:
        conn.close()
        raise HTTPException(status_code=404, detail="No output directory for this job.")

    session_id = job.get("session_id")
    ocr_rows = conn.execute(
        "SELECT frame_path, balance_value, bet_value, win_value, confidence_bal, confidence_bet, confidence_win "
        "FROM ocr_results WHERE session_id=? ORDER BY id",
        (session_id,),
    ).fetchall()
    conn.close()

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

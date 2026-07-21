"""
backend/routes/uploads.py
--------------------------
File upload intake. Validates, stores, and registers uploads.
Auto-triggers CSV parsing for .csv files.
Auto-triggers frame extraction for video files.

Maturity: Working Prototype
"""

import shutil
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, HTTPException, Form, BackgroundTasks, Request
from fastapi.responses import PlainTextResponse
from typing import Optional
from database.db import get_connection
from backend.services.csv_parser import parse_csv_file, generate_csv_template
from engines.video_pipeline import extract_frames
from backend.middleware.rate_limit import check_rate_limit, rate_limit_headers, get_client_ip

router = APIRouter(tags=["upload"])

BASE_DIR    = Path(__file__).resolve().parent.parent.parent
UPLOADS_DIR = BASE_DIR / "storage" / "uploads"
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)

ALLOWED_TYPES = {
    "text/csv":              "csv",
    "application/csv":       "csv",
    "video/mp4":             "video",
    "video/x-matroska":      "video",
    "video/quicktime":       "video",
    "video/x-msvideo":       "video",
    "image/png":             "image",
    "image/jpeg":            "image",
}


def _safe_filename(name: str) -> str:
    return "".join(c if c.isalnum() or c in "._-" else "_" for c in name)


def _unique_path(dest: Path) -> Path:
    stem, suffix, counter = dest.stem, dest.suffix, 1
    while dest.exists():
        dest = dest.parent / f"{stem}_{counter}{suffix}"
        counter += 1
    return dest


# ── Background tasks ──────────────────────────────────────────────────────────

def _bg_parse_csv(file_path: str, upload_id: int, session_id: int | None):
    """Run CSV parsing in the background after upload completes."""
    conn = get_connection()
    conn.execute("UPDATE uploads SET status='processing' WHERE id=?", (upload_id,))
    conn.commit()
    conn.close()

    result = parse_csv_file(file_path, upload_id, session_id)

    conn2 = get_connection()
    if result["success"]:
        conn2.execute("UPDATE uploads SET status='complete' WHERE id=?", (upload_id,))
    else:
        err = "; ".join(result["errors"])
        conn2.execute(
            "UPDATE uploads SET status='error', error_message=? WHERE id=?",
            (err, upload_id)
        )
    conn2.commit()
    conn2.close()


def _bg_extract_frames(video_path: str, upload_id: int):
    """Run FFmpeg frame extraction in background."""
    conn = get_connection()
    conn.execute("UPDATE uploads SET status='processing' WHERE id=?", (upload_id,))
    conn.commit()
    conn.close()

    result = extract_frames(video_path, fps=1.0)

    conn2 = get_connection()
    if result["success"]:
        conn2.execute(
            "UPDATE uploads SET status='complete', error_message=? WHERE id=?",
            (f"Extracted {result['frame_count']} frames to {result['output_dir']}", upload_id)
        )
    else:
        conn2.execute(
            "UPDATE uploads SET status='error', error_message=? WHERE id=?",
            (result["error"], upload_id)
        )
    conn2.commit()
    conn2.close()


# ── Routes ────────────────────────────────────────────────────────────────────

@router.post("")
async def upload_file(
    request: Request,
    background_tasks: BackgroundTasks,
    file:       UploadFile = File(...),
    session_id: Optional[int] = Form(None),
):
    """
    Accept a file, validate type, save to storage, register in DB.
    CSV files → auto-parsed into sessions + events (background task).
    Video files → frame extraction triggered (background task).
    Returns immediately with upload_id and status=processing.
    """
    limit_result = check_rate_limit(get_client_ip(request), "upload", max_calls=10, window_seconds=60)
    if not limit_result["allowed"]:
        raise HTTPException(
            status_code=429,
            detail=f"Too many uploads. Try again in {limit_result['reset_in']}s.",
            headers=rate_limit_headers(limit_result),
        )

    # Detect file type
    content_type = (file.content_type or "").split(";")[0].strip()
    file_type = ALLOWED_TYPES.get(content_type)

    # Fallback: detect by extension
    if not file_type and file.filename:
        ext = Path(file.filename).suffix.lower()
        ext_map = {".csv": "csv", ".mp4": "video", ".mkv": "video",
                   ".mov": "video", ".avi": "video", ".png": "image", ".jpg": "image"}
        file_type = ext_map.get(ext)

    if not file_type:
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported file type '{content_type}'. "
                   f"Accepted: CSV, MP4, MKV, MOV, AVI, PNG, JPEG."
        )

    safe_name = _safe_filename(file.filename or "upload")
    dest_path = _unique_path(UPLOADS_DIR / safe_name)

    with dest_path.open("wb") as f:
        shutil.copyfileobj(file.file, f)

    conn = get_connection()
    cur  = conn.execute(
        "INSERT INTO uploads (session_id, filename, file_type, file_path, status) "
        "VALUES (?, ?, ?, ?, ?)",
        (session_id, file.filename, file_type, str(dest_path),
         "processing" if file_type in ("csv", "video") else "complete")
    )
    upload_id = cur.lastrowid
    conn.commit()
    conn.close()

    # Trigger background processing
    if file_type == "csv":
        background_tasks.add_task(_bg_parse_csv, str(dest_path), upload_id, session_id)
        processing_note = "CSV file queued for parsing — sessions and events will appear shortly."
    elif file_type == "video":
        background_tasks.add_task(_bg_extract_frames, str(dest_path), upload_id)
        processing_note = "Video queued for frame extraction. Check upload status for progress."
    else:
        processing_note = "Image saved."

    return {
        "upload_id":        upload_id,
        "filename":         file.filename,
        "file_type":        file_type,
        "stored_at":        str(dest_path),
        "session_id":       session_id,
        "status":           "processing" if file_type in ("csv", "video") else "complete",
        "processing_note":  processing_note,
    }


@router.get("")
def list_uploads(session_id: Optional[int] = None):
    """Return upload history, optionally filtered by session."""
    conn = get_connection()
    if session_id:
        rows = conn.execute(
            "SELECT * FROM uploads WHERE session_id=? ORDER BY created_at DESC",
            (session_id,)
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM uploads ORDER BY created_at DESC LIMIT 200"
        ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


@router.get("/{upload_id}/status")
def get_upload_status(upload_id: int):
    """Poll status of a specific upload (for background processing)."""
    conn = get_connection()
    row  = conn.execute("SELECT * FROM uploads WHERE id=?", (upload_id,)).fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="Upload not found.")
    return dict(row)


@router.get("/template/{format_type}")
def download_template(format_type: str):
    """Download a CSV template. format_type: spin | session"""
    if format_type not in ("spin", "session"):
        raise HTTPException(status_code=400, detail="format_type must be 'spin' or 'session'.")
    content = generate_csv_template(format_type)
    return PlainTextResponse(
        content=content,
        headers={"Content-Disposition": f'attachment; filename="sessionguard_{format_type}_template.csv"'},
        media_type="text/csv",
    )

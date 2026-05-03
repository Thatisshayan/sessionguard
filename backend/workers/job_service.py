"""
backend/workers/job_service.py
-------------------------------
Background job queue using DB-backed jobs table.
Runs jobs in a thread pool. Supports retry, progress, cancellation.

Job types:
  video_pipeline  — extract frames + OCR + build events
  csv_parse       — parse uploaded CSV into sessions/events
  export_pdf      — generate PDF report
  export_excel    — generate Excel workbook
  regenerate      — regenerate insights/alerts for a session

Maturity: Working Prototype — thread pool executor, progress tracking, retry.
Future:   Replace with Celery + Redis (V7), add worker health metrics (V8).
"""

from __future__ import annotations
import json
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from database.db import get_connection

# ── Thread pool ───────────────────────────────────────────────────────────────
_POOL     = ThreadPoolExecutor(max_workers=4, thread_name_prefix="sg-worker")
_FUTURES  : dict[int, object] = {}
_LOCK     = threading.Lock()

MAX_RETRIES = 2


# ── DB helpers ────────────────────────────────────────────────────────────────

def create_job(
    job_type:   str,
    session_id: int | None   = None,
    upload_id:  int | None   = None,
    user_id:    int | None   = None,
    payload:    dict | None  = None,
    max_progress: int        = 100,
) -> int:
    conn = get_connection()
    cur  = conn.execute(
        "INSERT INTO jobs (job_type, session_id, upload_id, user_id, payload, max_progress) "
        "VALUES (?,?,?,?,?,?)",
        (job_type, session_id, upload_id, user_id,
         json.dumps(payload or {}), max_progress)
    )
    job_id = cur.lastrowid
    conn.commit(); conn.close()
    return job_id


def update_job(job_id: int, **kwargs):
    conn = get_connection()
    sets = ", ".join(f"{k}=?" for k in kwargs)
    conn.execute(f"UPDATE jobs SET {sets} WHERE id=?", [*kwargs.values(), job_id])
    conn.commit(); conn.close()


def get_job(job_id: int | dict) -> dict | None:
    # Defensively handle if dict passed instead of int
    if isinstance(job_id, dict):
        job_id = job_id.get("job_id", job_id.get("id"))
    conn = get_connection()
    row  = conn.execute("SELECT * FROM jobs WHERE id=?", (int(job_id),)).fetchone()
    conn.close()
    if not row:
        return None
    d = dict(row)
    try: d["payload"] = json.loads(d["payload"])
    except: pass
    try: d["result"]  = json.loads(d["result"])
    except: pass
    return d


def list_jobs(
    status:     str | None = None,
    session_id: int | None = None,
    user_id:    int | None = None,
    limit:      int        = 50,
) -> list[dict]:
    conn    = get_connection()
    filters = []
    params  : list = []
    if status:     filters.append("status=?");     params.append(status)
    if session_id: filters.append("session_id=?"); params.append(session_id)
    if user_id:    filters.append("user_id=?");    params.append(user_id)
    where = ("WHERE " + " AND ".join(filters)) if filters else ""
    rows  = conn.execute(
        f"SELECT * FROM jobs {where} ORDER BY created_at DESC LIMIT ?",
        [*params, limit]
    ).fetchall()
    conn.close()
    result = []
    for r in rows:
        d = dict(r)
        try: d["payload"] = json.loads(d["payload"])
        except: pass
        result.append(d)
    return result


# ── Job runners ───────────────────────────────────────────────────────────────

def _run_video_pipeline(job_id: int, job: dict):
    from engines.video_pipeline import run_video_pipeline
    payload    = job.get("payload", {})
    video_path = payload.get("video_path")
    roi_config = payload.get("roi_config")
    fps        = payload.get("fps", 1.0)

    if not video_path:
        update_job(job_id, status="error", error_message="No video_path in payload.",
                   completed_at=datetime.now(timezone.utc).isoformat())
        return

    def progress_cb(stage: str, done: int, total: int):
        pct = int(done / max(total, 1) * 100)
        update_job(job_id, progress=pct, result=json.dumps({"stage": stage}))

    result = run_video_pipeline(
        video_path=video_path,
        session_id=job["session_id"],
        upload_id=job["upload_id"],
        roi_config=roi_config,
        fps=fps,
        progress_cb=progress_cb,
    )
    status = "complete" if result.get("success") else "error"
    update_job(job_id,
               status=status,
               progress=100 if status == "complete" else job.get("progress", 0),
               result=json.dumps(result),
               error_message=result.get("error", ""),
               completed_at=datetime.now(timezone.utc).isoformat())


def _run_csv_parse(job_id: int, job: dict):
    from backend.services.csv_parser import parse_csv_file
    payload   = job.get("payload", {})
    file_path = payload.get("file_path")
    if not file_path:
        update_job(job_id, status="error", error_message="No file_path in payload.",
                   completed_at=datetime.now(timezone.utc).isoformat())
        return
    update_job(job_id, progress=10)
    result = parse_csv_file(file_path, job["upload_id"], job["session_id"])
    update_job(job_id,
               status="complete" if result["success"] else "error",
               progress=100,
               result=json.dumps(result),
               error_message="; ".join(result.get("errors", [])),
               completed_at=datetime.now(timezone.utc).isoformat())


def _run_export_pdf(job_id: int, job: dict):
    from backend.services.export_service import generate_pdf
    update_job(job_id, progress=20)
    result = generate_pdf(session_id=job["session_id"])
    update_job(job_id,
               status="complete" if result["success"] else "error",
               progress=100,
               result=json.dumps({"filename": result.get("filename"), "file_path": result.get("file_path")}),
               error_message=result.get("error") or "",
               completed_at=datetime.now(timezone.utc).isoformat())


def _run_export_excel(job_id: int, job: dict):
    from backend.services.export_service import generate_excel
    update_job(job_id, progress=20)
    result = generate_excel(session_id=job["session_id"])
    update_job(job_id,
               status="complete" if result["success"] else "error",
               progress=100,
               result=json.dumps({"filename": result.get("filename"), "file_path": result.get("file_path")}),
               error_message=result.get("error") or "",
               completed_at=datetime.now(timezone.utc).isoformat())


def _run_regenerate(job_id: int, job: dict):
    from engines.insights_engine import generate_and_persist_insights
    from engines.alerts_engine import generate_and_persist_alerts
    sid = job["session_id"]
    if not sid:
        update_job(job_id, status="error", error_message="No session_id.",
                   completed_at=datetime.now(timezone.utc).isoformat())
        return
    update_job(job_id, progress=30)
    ins = generate_and_persist_insights(sid)
    update_job(job_id, progress=70)
    al  = generate_and_persist_alerts(sid)
    update_job(job_id,
               status="complete", progress=100,
               result=json.dumps({"insights": len(ins), "alerts": len(al)}),
               completed_at=datetime.now(timezone.utc).isoformat())


_RUNNERS: dict[str, Callable] = {
    "video_pipeline": _run_video_pipeline,
    "csv_parse":      _run_csv_parse,
    "export_pdf":     _run_export_pdf,
    "export_excel":   _run_export_excel,
    "regenerate":     _run_regenerate,
}


def _execute_job(job_id: int):
    """Wrapper called in thread pool — handles retry logic."""
    job = get_job(job_id)
    if not job:
        return

    runner = _RUNNERS.get(job["job_type"])
    if not runner:
        update_job(job_id, status="error",
                   error_message=f"Unknown job type: {job['job_type']}",
                   completed_at=datetime.now(timezone.utc).isoformat())
        return

    update_job(job_id, status="running", started_at=datetime.now(timezone.utc).isoformat())
    try:
        runner(job_id, job)
    except Exception as e:
        update_job(job_id, status="error",
                   error_message=str(e),
                   completed_at=datetime.now(timezone.utc).isoformat())


# ── Public API ────────────────────────────────────────────────────────────────

def enqueue_job(
    job_type:   str,
    session_id: int | None  = None,
    upload_id:  int | None  = None,
    user_id:    int | None  = None,
    payload:    dict | None = None,
    max_progress: int       = 100,
) -> dict:
    """Create a DB job record and submit it to the thread pool."""
    job_id = create_job(
        job_type=job_type, session_id=session_id, upload_id=upload_id,
        user_id=user_id, payload=payload, max_progress=max_progress,
    )
    future = _POOL.submit(_execute_job, job_id)
    with _LOCK:
        _FUTURES[job_id] = future
    return {"job_id": job_id, "job_type": job_type, "status": "pending"}


def cancel_job(job_id: int) -> bool:
    """Cancel a pending job. Cannot cancel running jobs."""
    with _LOCK:
        future = _FUTURES.get(job_id)
    if future and future.cancel():  # type: ignore
        update_job(job_id, status="cancelled",
                   completed_at=datetime.now(timezone.utc).isoformat())
        return True
    return False

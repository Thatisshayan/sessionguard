"""
backend/workers/job_service.py
-------------------------------
Background job queue using DB-backed jobs table.
Runs jobs in a thread pool. Supports retry with backoff, progress, cancellation.

Job types:
  video_pipeline  — extract frames + OCR + build events
  csv_parse       — parse uploaded CSV into sessions/events
  export_pdf      — generate PDF report
  export_excel    — generate Excel workbook
  regenerate      — regenerate insights/alerts for a session

Maturity: Enhanced Prototype — thread pool executor, retry with backoff,
          WebSocket progress, cooperative cancellation, worker health.
Future:   Replace with Celery + Redis (V7), add distributed worker metrics (V8).
"""

from __future__ import annotations
import json
import logging
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, Future
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Any

import structlog
from database.db import get_connection

# ── Configuration ─────────────────────────────────────────────────────────────
MAX_WORKERS = 4
MAX_RETRIES = 3
BASE_RETRY_DELAY = 2.0  # seconds
MAX_RETRY_DELAY = 60.0  # seconds
PROGRESS_BROADCAST_INTERVAL = 1.0  # seconds between WebSocket progress pushes

# ── Thread pool & worker state ────────────────────────────────────────────────
_POOL: ThreadPoolExecutor = ThreadPoolExecutor(max_workers=MAX_WORKERS, thread_name_prefix="sg-worker")
_FUTURES: dict[int, Future] = {}
_JOB_CANCEL_FLAGS: dict[int, threading.Event] = {}
_WORKER_METADATA: dict[int, dict] = {}
_LOCK = threading.Lock()

# Structured logger
log = structlog.get_logger("job_service")


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


# ── Retry helpers ─────────────────────────────────────────────────────────────

def _calc_retry_delay(attempt: int) -> float:
    """Exponential backoff with jitter: BASE * 2^attempt, capped at MAX."""
    import random
    delay = BASE_RETRY_DELAY * (2 ** attempt)
    delay = min(delay, MAX_RETRY_DELAY)
    return delay + random.uniform(0, 0.5)


# ── Job runners ───────────────────────────────────────────────────────────────

def _is_cancelled(job_id: int) -> bool:
    """Check if job has been cancelled."""
    flag = _JOB_CANCEL_FLAGS.get(job_id)
    return flag.is_set() if flag else False


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
        if _is_cancelled(job_id):
            raise KeyboardInterrupt("Job cancelled")
        pct = int(done / max(total, 1) * 100)
        update_job(job_id, progress=pct, result=json.dumps({"stage": stage}))
        _broadcast_progress(job_id, pct, stage)

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


# ── WebSocket progress broadcast ──────────────────────────────────────────────

async def _broadcast_progress(job_id: int, progress: int, stage: str):
    """Push progress update to WebSocket subscribers."""
    try:
        from backend.routes.ws import push_sync, push_job_progress
        job = get_job(job_id)
        if job:
            await push_sync(push_job_progress(
                job_id=job_id,
                progress=progress,
                stage=stage,
                session_id=job.get("session_id")
            ))
    except Exception:
        pass  # WebSocket push is best-effort


# ── Job execution wrapper with retry/backoff ──────────────────────────────────

def _execute_job(job_id: int):
    """Wrapper called in thread pool — handles retry logic with exponential backoff."""
    job = get_job(job_id)
    if not job:
        return

    runner = _RUNNERS.get(job["job_type"])
    if not runner:
        update_job(job_id, status="error",
                   error_message=f"Unknown job type: {job['job_type']}",
                   completed_at=datetime.now(timezone.utc).isoformat())
        return

    attempt = job.get("attempt", 0)
    update_job(job_id, status="running", started_at=datetime.now(timezone.utc).isoformat(), attempt=attempt)

    while attempt <= MAX_RETRIES:
        if _is_cancelled(job_id):
            update_job(job_id, status="cancelled",
                       completed_at=datetime.now(timezone.utc).isoformat())
            log.info("job_cancelled", job_id=job_id, job_type=job["job_type"])
            return

        try:
            runner(job_id, job)
            # If runner completes without exception, job is done
            return
        except KeyboardInterrupt:
            # Cancellation signal
            update_job(job_id, status="cancelled",
                       completed_at=datetime.now(timezone.utc).isoformat())
            log.info("job_cancelled_during_execution", job_id=job_id)
            return
        except Exception as e:
            attempt += 1
            if attempt > MAX_RETRIES:
                update_job(job_id, status="error",
                           error_message=f"Failed after {MAX_RETRIES} retries: {str(e)}",
                           completed_at=datetime.now(timezone.utc).isoformat())
                log.error("job_failed", job_id=job_id, job_type=job["job_type"],
                          attempt=attempt, error=str(e))
                return

            delay = _calc_retry_delay(attempt - 1)
            log.warning("job_retry", job_id=job_id, attempt=attempt,
                        max_retries=MAX_RETRIES, delay_seconds=round(delay, 2))
            update_job(job_id, status="pending", attempt=attempt,
                       error_message=f"Retry {attempt}/{MAX_RETRIES} in {delay:.1f}s: {str(e)}")
            time.sleep(delay)


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
        _JOB_CANCEL_FLAGS[job_id] = threading.Event()
        _WORKER_METADATA[job_id] = {
            "submitted_at": datetime.now(timezone.utc).isoformat(),
            "job_type": job_type,
        }
    log.info("job_enqueued", job_id=job_id, job_type=job_type,
             session_id=session_id, worker_count=len(_FUTURES))
    return {"job_id": job_id, "job_type": job_type, "status": "pending"}


def cancel_job(job_id: int) -> bool:
    """Cancel a pending or running job by setting cancellation flag."""
    with _LOCK:
        flag = _JOB_CANCEL_FLAGS.get(job_id)
    if flag:
        flag.set()
    # Also try to cancel the future if still pending
    with _LOCK:
        future = _FUTURES.get(job_id)
    if future and future.cancel():
        update_job(job_id, status="cancelled",
                   completed_at=datetime.now(timezone.utc).isoformat())
        log.info("job_cancelled_via_future", job_id=job_id)
        return True
    # If running, the flag will be checked by the runner
    job = get_job(job_id)
    if job and job.get("status") == "running":
        return True
    return False


def get_worker_health() -> dict:
    """Return worker pool health status."""
    with _LOCK:
        active = sum(1 for f in _FUTURES.values() if f.running())
        pending = sum(1 for f in _FUTURES.values() if not f.done())
    return {
        "max_workers": MAX_WORKERS,
        "active_jobs": active,
        "pending_jobs": pending,
        "total_submitted": len(_FUTURES),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def cleanup_completed_jobs(max_age_seconds: int = 3600) -> int:
    """Remove completed job futures/metadata older than max_age_seconds."""
    from datetime import timedelta
    cutoff = datetime.now(timezone.utc) - timedelta(seconds=max_age_seconds)
    removed = 0
    with _LOCK:
        to_remove = []
        for job_id, meta in _WORKER_METADATA.items():
            submitted = datetime.fromisoformat(meta["submitted_at"])
            if submitted < cutoff:
                future = _FUTURES.get(job_id)
                if future and future.done():
                    to_remove.append(job_id)
        for job_id in to_remove:
            _FUTURES.pop(job_id, None)
            _JOB_CANCEL_FLAGS.pop(job_id, None)
            _WORKER_METADATA.pop(job_id, None)
            removed += 1
    return removed

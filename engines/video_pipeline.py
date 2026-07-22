"""
engines/video_pipeline.py
--------------------------
Real video processing pipeline using OpenCV + Tesseract.

Pipeline stages:
  1. FFmpeg availability check
  2. Frame extraction via cv2 (scene-change-aware)
  3. OCR pass over each frame (extract balance/bet/win)
  4. Event builder: convert OCR outputs to structured events
  5. Review queue population for low-confidence detections
  6. Persist results to DB (video_jobs, ocr_results, events)

Maturity: Working Prototype — all stages real and wired.
Future:   ROI auto-calibration (V8), multi-region per frame (V9).
"""

from __future__ import annotations
import json
import shutil
import subprocess
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from typing import Callable, Optional
import cv2
import numpy as np

from database.db import get_connection
from engines.ocr_engine import (
    extract_fields_from_image,
    persist_ocr_result,
    CONFIDENCE_THRESHOLD,
)

BASE_DIR    = Path(__file__).resolve().parent.parent
STORAGE_DIR = BASE_DIR / "storage"
FRAMES_DIR  = STORAGE_DIR / "recordings"


# ── Perceptual hash for scene-change dedup ────────────────────────────────────

def _phash(image_path: str, hash_size: int = 8) -> int:
    """
    Compute a perceptual hash (pHash) for an image using DCT.
    Returns an integer hash; hamming distance between hashes indicates similarity.
    """
    img = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
    if img is None:
        return 0
    # Resize to hash_size*4 x hash_size*4 for DCT
    resized = cv2.resize(img, (hash_size * 4, hash_size * 4), interpolation=cv2.INTER_AREA)
    # Float and DCT
    float_img = np.float32(resized)
    dct = cv2.dct(float_img)
    # Keep top-left hash_size x hash_size (low frequencies)
    dct_low = dct[:hash_size, :hash_size]
    # Median threshold
    median = np.median(dct_low)
    # Binary hash: 1 if above median, 0 otherwise
    bits = (dct_low > median).flatten()
    # Convert to integer
    hash_val = 0
    for bit in bits:
        hash_val = (hash_val << 1) | int(bit)
    return hash_val


def _hamming_distance(h1: int, h2: int) -> int:
    """Count differing bits between two hashes."""
    return bin(h1 ^ h2).count('1')


# ── Top-level worker for parallel OCR (must be picklable for ProcessPoolExecutor) ──

def _ocr_worker(args: tuple) -> dict:
    """Run OCR on a single frame. Designed for ProcessPoolExecutor."""
    path, roi_config = args
    from engines.ocr_engine import extract_fields_from_image
    return extract_fields_from_image(path, roi_config=roi_config)


# ── 1. Dependency check ───────────────────────────────────────────────────────

def check_ffmpeg() -> dict:
    """Verify FFmpeg is installed and on PATH. Safe to call at any time."""
    path = shutil.which("ffmpeg")
    if not path:
        return {
            "available": False,
            "path":      None,
            "version":   None,
            "message":   "FFmpeg not found. Install from https://ffmpeg.org/download.html",
        }
    try:
        r = subprocess.run(
            ["ffmpeg", "-version"],
            capture_output=True, text=True, timeout=5
        )
        version = r.stdout.splitlines()[0] if r.stdout else "unknown"
        return {"available": True, "path": path, "version": version, "message": "FFmpeg ready."}
    except Exception as e:
        return {"available": False, "path": path, "version": None, "message": str(e)}


# ── 2. Frame extraction ───────────────────────────────────────────────────────

def extract_frames(
    video_path: str,
    fps: float = 1.0,
    output_dir: Optional[str] = None,
    scene_threshold: float = 18.0,
) -> dict:
    """
    Extract frames from a video at `fps` frames per second.
    Computes scene-change diff score between consecutive frames.

    Returns:
        success, output_dir, frame_count, frames list (path + metadata), error
    """
    video = Path(video_path)
    if not video.exists():
        return {"success": False, "error": f"Video not found: {video_path}", "frames": []}

    out_dir = Path(output_dir) if output_dir else FRAMES_DIR / video.stem
    out_dir.mkdir(parents=True, exist_ok=True)

    cap = cv2.VideoCapture(str(video))
    if not cap.isOpened():
        return {"success": False, "error": "Could not open video with OpenCV.", "frames": []}

    native_fps    = cap.get(cv2.CAP_PROP_FPS) or 25.0
    frame_interval = max(1, int(native_fps / fps))
    frame_idx      = 0
    saved          = 0
    frames         = []
    prev_gray      = None

    while True:
        ok, frame = cap.read()
        if not ok:
            break

        if frame_idx % frame_interval == 0:
            ts    = round(frame_idx / native_fps, 2)
            gray  = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

            scene_changed = False
            diff_score    = 0.0
            if prev_gray is not None:
                diff       = cv2.absdiff(gray, prev_gray)
                diff_score = float(diff.mean())
                scene_changed = diff_score >= scene_threshold

            prev_gray = gray

            frame_path = out_dir / f"frame_{saved:04d}.jpg"
            cv2.imwrite(str(frame_path), frame)

            frames.append({
                "frame_index":        frame_idx,
                "saved_index":        saved,
                "timestamp_seconds":  ts,
                "scene_changed":      scene_changed,
                "diff_score":         round(diff_score, 2),
                "stored_path":        str(frame_path),
            })
            saved += 1

        frame_idx += 1

    cap.release()

    scene_changes = [f["timestamp_seconds"] for f in frames if f["scene_changed"]]
    return {
        "success":            True,
        "output_dir":         str(out_dir),
        "frame_count":        saved,
        "scene_change_count": len(scene_changes),
        "scene_changes":      scene_changes,
        "frames":             frames,
        "error":              None,
    }


# ── 3. OCR pass over frames ───────────────────────────────────────────────────

def ocr_frames(
    frames: list[dict],
    roi_config: dict | None = None,
    session_id: int | None  = None,
    upload_id: int | None   = None,
    progress_cb: Optional[Callable[[int, int], None]] = None,
    workers: int = 1,
    dedup_threshold: int = 0,
) -> list[dict]:
    """
    Run OCR on each extracted frame.
    Returns list of per-frame OCR results (fields + confidence + flagged).
    Persists results to ocr_results table.

    workers: number of parallel OCR workers (default 1 = sequential).
    dedup_threshold: hamming distance threshold for pHash dedup (0 = disabled).
                     Frames with distance < threshold to the last processed frame
                     are skipped (OCR result copied from last frame).
                     Recommended: 5-10 for typical slot machine videos.
    """
    from engines.ocr_engine import persist_ocr_result

    total = len(frames)
    last_hash = None
    last_ocr = None

    if workers > 1:
        # Parallel OCR with dedup: pre-compute hashes, filter, then dispatch
        if dedup_threshold > 0:
            frames_to_process = []
            skip_indices = set()
            last_h = None
            for i, frame_info in enumerate(frames):
                h = _phash(frame_info["stored_path"])
                if last_h is not None and _hamming_distance(h, last_h) < dedup_threshold:
                    skip_indices.add(i)
                else:
                    last_h = h
                    frames_to_process.append((i, frame_info))

            # Process only non-duplicate frames
            tasks = [(fi["stored_path"], roi_config) for _, fi in frames_to_process]
            ocr_map = {}

            with ProcessPoolExecutor(max_workers=workers) as pool:
                futures = {}
                for i, (orig_idx, _) in enumerate(frames_to_process):
                    f = pool.submit(_ocr_worker, tasks[i])
                    futures[f] = orig_idx

                for future in as_completed(futures):
                    orig_idx = futures[future]
                    try:
                        ocr_map[orig_idx] = future.result()
                    except Exception:
                        ocr_map[orig_idx] = {"fields": {}, "flagged": True, "overall_confidence": 0.0}

            # Build results: fill skipped frames with previous result
            raw_results = [None] * total
            last_result = None
            for i in range(total):
                if i in ocr_map:
                    last_result = ocr_map[i]
                    raw_results[i] = last_result
                elif last_result is not None:
                    raw_results[i] = {**last_result, "_deduped": True}
                else:
                    raw_results[i] = {"fields": {}, "flagged": True, "overall_confidence": 0.0}

            if progress_cb:
                progress_cb(total, total)
        else:
            # No dedup: dispatch all frames
            tasks = [(f["stored_path"], roi_config) for f in frames]
            raw_results = [None] * total

            with ProcessPoolExecutor(max_workers=workers) as pool:
                future_to_idx = {pool.submit(_ocr_worker, task): i for i, task in enumerate(tasks)}
                for future in as_completed(future_to_idx):
                    idx = future_to_idx[future]
                    try:
                        raw_results[idx] = future.result()
                    except Exception:
                        raw_results[idx] = {"fields": {}, "flagged": True, "overall_confidence": 0.0}
                    if progress_cb:
                        progress_cb(sum(1 for r in raw_results if r is not None), total)

        # Attach frame metadata + persist sequentially
        results = []
        for i, (frame_info, ocr) in enumerate(zip(frames, raw_results)):
            if ocr is None:
                ocr = {"fields": {}, "flagged": True, "overall_confidence": 0.0}
            ocr["timestamp_seconds"] = frame_info["timestamp_seconds"]
            ocr["scene_changed"]     = frame_info["scene_changed"]
            ocr["diff_score"]        = frame_info["diff_score"]

            result_id = persist_ocr_result(
                frame_path=frame_info["stored_path"],
                fields=ocr,
                session_id=session_id,
                upload_id=upload_id,
            )
            ocr["ocr_result_id"] = result_id
            results.append(ocr)
    else:
        # Sequential OCR with optional dedup
        results = []
        for i, frame_info in enumerate(frames):
            path = frame_info["stored_path"]

            # Dedup check: skip OCR if frame is too similar to last
            skip = False
            if dedup_threshold > 0:
                h = _phash(path)
                if last_hash is not None and _hamming_distance(h, last_hash) < dedup_threshold:
                    skip = True
                else:
                    last_hash = h

            if skip and last_ocr is not None:
                fields = {**last_ocr, "_deduped": True}
            else:
                fields = extract_fields_from_image(path, roi_config=roi_config)
                last_ocr = fields
                if dedup_threshold > 0 and last_hash is None:
                    last_hash = _phash(path)

            fields["timestamp_seconds"] = frame_info["timestamp_seconds"]
            fields["scene_changed"]     = frame_info["scene_changed"]
            fields["diff_score"]        = frame_info["diff_score"]

            result_id = persist_ocr_result(
                frame_path=path,
                fields=fields,
                session_id=session_id,
                upload_id=upload_id,
            )
            fields["ocr_result_id"] = result_id
            results.append(fields)

            if progress_cb:
                progress_cb(i + 1, total)

    return results


# ── 4. Event building ─────────────────────────────────────────────────────────

def build_events_from_ocr(
    ocr_results: list[dict],
    session_id: int,
    base_timestamp: Optional[str] = None,
) -> tuple[int, int]:
    """
    Convert OCR frame results into session events.
    Only creates an event when balance field is detected (implies a spin read).

    Returns (events_created, review_items_created).
    """
    conn           = get_connection()
    events_created = 0
    review_created = 0
    base_ts        = base_timestamp or datetime.now().isoformat()

    prev_balance = None

    for ocr in ocr_results:
        f          = ocr.get("fields", {})
        balance    = f.get("balance", {}).get("value")
        bet        = f.get("bet",     {}).get("value")
        win        = f.get("win",     {}).get("value")
        conf_avg   = ocr.get("overall_confidence", 0.0)
        ts_offset  = ocr.get("timestamp_seconds", 0)

        # Only build event if we have balance data
        if balance is None:
            continue

        # Derive win amount from balance delta if not directly detected
        if win is None and prev_balance is not None and bet is not None:
            implied_win = round(balance - prev_balance + (bet or 0), 2)
            win = max(0.0, implied_win)

        prev_balance = balance

        # Insert event
        ts = f"{base_ts[:10]}T{int(ts_offset // 3600):02d}:{int((ts_offset % 3600) // 60):02d}:{int(ts_offset % 60):02d}"
        cur = conn.execute(
            """INSERT INTO events
               (session_id, timestamp, event_type, bet_amount,
                win_amount, balance_after, confidence_score, source)
               VALUES (?,?,?,?,?,?,?,'ocr')""",
            (session_id, ts, "spin",
             bet or 0.0, win or 0.0, balance, conf_avg)
        )
        events_created += 1

        # Flag low-confidence events for review queue
        if conf_avg < CONFIDENCE_THRESHOLD or ocr.get("flagged"):
            conn.execute(
                """INSERT INTO review_items
                   (session_id, event_id, reason, status)
                   VALUES (?,?,?,'pending')""",
                (session_id, cur.lastrowid,
                 f"OCR confidence {conf_avg:.2f} — balance ${balance:.2f} may be inaccurate.")
            )
            review_created += 1

    conn.commit()
    conn.close()
    return events_created, review_created


# ── 5. Full pipeline orchestrator ─────────────────────────────────────────────

def run_video_pipeline(
    video_path: str,
    session_id: int,
    upload_id: int,
    roi_config: dict | None = None,
    fps: float = 1.0,
    progress_cb: Optional[Callable[[str, int, int], None]] = None,
    workers: int = 1,
    dedup_threshold: int = 0,
) -> dict:
    """
    Run the full video → frames → OCR → events pipeline.
    Updates video_jobs table throughout for progress tracking.

    progress_cb(stage, current, total) called at each stage.
    workers: number of parallel OCR workers (default 1 = sequential).
    dedup_threshold: pHash hamming distance threshold for scene dedup (0 = disabled).
    """
    conn = get_connection()
    job_cur = conn.execute(
        """INSERT INTO video_jobs
           (session_id, upload_id, status, started_at)
           VALUES (?,?,'running',datetime('now'))""",
        (session_id, upload_id)
    )
    job_id = job_cur.lastrowid
    conn.commit()
    conn.close()

    def _update_job(**kwargs):
        c = get_connection()
        sets = ", ".join(f"{k}=?" for k in kwargs)
        c.execute(f"UPDATE video_jobs SET {sets} WHERE id=?",
                  [*kwargs.values(), job_id])
        c.commit()
        c.close()

    try:
        # ── Stage 1: Extract frames ───────────────────────────────────────────
        if progress_cb:
            progress_cb("extracting_frames", 0, 1)

        out_dir = FRAMES_DIR / Path(video_path).stem
        frame_result = extract_frames(video_path, fps=fps, output_dir=str(out_dir))

        if not frame_result["success"]:
            _update_job(status="error", error_message=frame_result["error"],
                        completed_at="datetime('now')")
            return {"success": False, "error": frame_result["error"], "job_id": job_id}

        frames = frame_result["frames"]
        _update_job(
            frames_extracted=len(frames),
            scene_changes=frame_result["scene_change_count"],
            output_dir=str(out_dir),
        )
        if progress_cb:
            progress_cb("extracting_frames", len(frames), len(frames))

        # ── Stage 2: OCR pass ─────────────────────────────────────────────────
        def ocr_progress(done, total):
            _update_job(frames_ocr_done=done)
            if progress_cb:
                progress_cb("ocr_pass", done, total)

        ocr_results = ocr_frames(
            frames,
            roi_config=roi_config,
            session_id=session_id,
            upload_id=upload_id,
            progress_cb=ocr_progress,
            workers=workers,
            dedup_threshold=dedup_threshold,
        )
        _update_job(frames_ocr_done=len(ocr_results))

        # ── Stage 3: Build events ─────────────────────────────────────────────
        if progress_cb:
            progress_cb("building_events", 0, 1)

        events_n, review_n = build_events_from_ocr(ocr_results, session_id)
        _update_job(events_built=events_n)

        if progress_cb:
            progress_cb("building_events", events_n, events_n)

        # ── Stage 4: Validate events ──────────────────────────────────────────
        from engines.event_validator import validate_session_events
        post_conn = get_connection()
        post_events = [
            dict(r) for r in post_conn.execute(
                "SELECT id, session_id, bet_amount, win_amount, balance_after, confidence_score "
                "FROM events WHERE session_id=? ORDER BY timestamp",
                (session_id,),
            ).fetchall()
        ]
        post_conn.close()
        validation = validate_session_events(post_events)
        if progress_cb:
            progress_cb("validation", len(post_events), len(post_events))

        # ── Stage 5: Update session metrics from new events ───────────────────
        _recalc_session_from_events(session_id)

        # ── Finalise ──────────────────────────────────────────────────────────
        _update_job(
            status="complete",
            completed_at="datetime('now')",
        )

        return {
            "success":        True,
            "job_id":         job_id,
            "frames_extracted": len(frames),
            "scene_changes":  frame_result["scene_change_count"],
            "ocr_frames":     len(ocr_results),
            "events_created": events_n,
            "review_items":   review_n,
            "output_dir":     str(out_dir),
        }

    except Exception as e:
        _update_job(status="error", error_message=str(e))
        return {"success": False, "error": str(e), "job_id": job_id}


def _recalc_session_from_events(session_id: int):
    """Recompute session aggregate metrics from real events."""
    conn = get_connection()
    events = conn.execute(
        "SELECT bet_amount, win_amount, balance_after FROM events WHERE session_id=? ORDER BY timestamp",
        (session_id,)
    ).fetchall()

    if not events:
        conn.close()
        return

    total_bets  = sum(e["bet_amount"] or 0 for e in events)
    total_wins  = sum(e["win_amount"]  or 0 for e in events)
    spins       = len(events)
    biggest_win = max((e["win_amount"] or 0 for e in events), default=0)
    end_balance = events[-1]["balance_after"] or 0

    # Losing streak
    streak = max_streak = 0
    for e in events:
        if (e["win_amount"] or 0) == 0:
            streak += 1
            max_streak = max(max_streak, streak)
        else:
            streak = 0

    rtp = round(total_wins / total_bets * 100, 2) if total_bets > 0 else 0

    conn.execute(
        """UPDATE sessions SET
           total_bets=?, total_wins=?, spins=?, biggest_win=?,
           losing_streak=?, rtp=?, end_balance=?,
           net_result=round(end_balance - start_balance, 2)
           WHERE id=?""",
        (round(total_bets, 2), round(total_wins, 2), spins,
         round(biggest_win, 2), max_streak, rtp, round(end_balance, 2), session_id)
    )
    conn.commit()
    conn.close()


def get_video_job(job_id: int) -> dict | None:
    """Return video processing job status."""
    conn = get_connection()
    row  = conn.execute("SELECT * FROM video_jobs WHERE id=?", (job_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def get_video_jobs_for_session(session_id: int) -> list[dict]:
    """Return all video jobs for a session."""
    conn  = get_connection()
    rows  = conn.execute(
        "SELECT * FROM video_jobs WHERE session_id=? ORDER BY created_at DESC",
        (session_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]

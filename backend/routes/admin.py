"""
backend/routes/admin.py
------------------------
Admin-only endpoints for system health, user management, audit log.

Maturity: Working Prototype
Future:   Add system metrics dashboard, quota management, org controls (V14).
"""

import asyncio
import sqlite3
import tempfile
import time
from pathlib import Path
from fastapi import APIRouter, File, HTTPException, Header, Query, UploadFile
from pydantic import BaseModel
from typing import Optional
import database.db as db_module
from database.db import get_connection, async_fetch_one, async_fetch_all, async_execute
from backend.auth.service import get_current_user_from_token, hash_password
from backend.auth.access import require_admin as _require_admin

router = APIRouter(tags=["admin"])


# ── System health ─────────────────────────────────────────────────────────────

@router.get("/health")
async def system_health(authorization: Optional[str] = Header(None)):
    """Full system health — DB stats, table counts, engine status."""
    await _require_admin(authorization)
    tables_row = await async_fetch_all(
        "SELECT name FROM sqlite_master WHERE type='table'"
    )
    tables = [r[0] for r in tables_row]

    counts = {}
    for t in tables:
        try:
            row = await async_fetch_one(f"SELECT COUNT(*) AS cnt FROM {t}")
            counts[t] = row["cnt"] if row else -1
        except Exception:
            counts[t] = -1

    from engines.video_pipeline import check_ffmpeg
    from engines.ocr_engine import check_ocr_status
    ffmpeg = await asyncio.to_thread(check_ffmpeg)
    ocr    = await asyncio.to_thread(check_ocr_status)

    return {
        "status":      "ok",
        "tables":      len(tables),
        "table_counts": counts,
        "dependencies": {
            "ffmpeg":    ffmpeg["available"],
            "tesseract": ocr["backends"]["tesseract"]["available"],
        },
    }


@router.get("/stats")
async def system_stats(authorization: Optional[str] = Header(None)):
    """Platform-wide statistics."""
    await _require_admin(authorization)
    r = await async_fetch_one("""
        SELECT
            (SELECT COUNT(*) FROM sessions)      AS sessions,
            (SELECT COUNT(*) FROM events)        AS events,
            (SELECT COUNT(*) FROM users)         AS users,
            (SELECT COUNT(*) FROM projects)      AS projects,
            (SELECT COUNT(*) FROM review_items WHERE status='pending') AS pending_reviews,
            (SELECT COUNT(*) FROM alerts WHERE acknowledged=0) AS unacked_alerts,
            (SELECT COUNT(*) FROM jobs WHERE status='running') AS running_jobs,
            (SELECT COUNT(*) FROM exports)       AS exports
    """)
    return dict(r)


# ── User management ───────────────────────────────────────────────────────────

@router.get("/users")
async def list_all_users(
    authorization: Optional[str] = Header(None),
    limit: int = Query(100, le=500),
):
    await _require_admin(authorization)
    rows = await async_fetch_all(
        "SELECT id, email, username, role, is_active, created_at, last_login "
        "FROM users ORDER BY created_at DESC LIMIT ?", (limit,)
    )
    return rows


class UserRoleUpdate(BaseModel):
    role:      Optional[str] = None
    is_active: Optional[bool] = None


@router.patch("/users/{user_id}")
async def update_user(user_id: int, body: UserRoleUpdate,
                authorization: Optional[str] = Header(None)):
    admin = await _require_admin(authorization)
    updates = {k: v for k, v in body.dict().items() if v is not None}
    if not updates:
        return {"message": "Nothing to update."}
    if not await async_fetch_one("SELECT id FROM users WHERE id=?", (user_id,)):
        raise HTTPException(status_code=404, detail="User not found.")
    set_clause = ", ".join(f"{k}=?" for k in updates)
    await async_execute(f"UPDATE users SET {set_clause} WHERE id=?",
                 (*updates.values(), user_id))
    return {"user_id": user_id, "updated": list(updates.keys())}


@router.delete("/users/{user_id}", status_code=204)
async def delete_user(user_id: int, authorization: Optional[str] = Header(None)):
    admin = await _require_admin(authorization)
    if admin["user_id"] == user_id:
        raise HTTPException(status_code=400, detail="Cannot delete your own account.")
    rowcount = await async_execute("DELETE FROM users WHERE id=?", (user_id,))
    if rowcount == 0:
        raise HTTPException(status_code=404, detail="User not found.")


# ── Audit log ─────────────────────────────────────────────────────────────────

@router.get("/audit")
async def audit_log(
    authorization: Optional[str] = Header(None),
    user_id: Optional[int] = Query(None),
    action:  Optional[str] = Query(None),
    limit:   int           = Query(100, le=500),
):
    await _require_admin(authorization)
    filters = []
    params  : list = []
    if user_id: filters.append("a.user_id=?"); params.append(user_id)
    if action:  filters.append("a.action LIKE ?"); params.append(f"%{action}%")
    where = ("WHERE " + " AND ".join(filters)) if filters else ""
    rows = await async_fetch_all(
        f"SELECT a.*, u.email, u.username FROM audit_log a "
        f"LEFT JOIN users u ON u.id = a.user_id "
        f"{where} ORDER BY a.created_at DESC LIMIT ?",
        (*params, limit)
    )
    return rows


@router.get("/backup")
async def backup_database(authorization: Optional[str] = Header(None)):
    """Create a consistent SQLite database backup via VACUUM INTO."""
    await _require_admin(authorization)
    import tempfile
    from pathlib import Path
    from fastapi.responses import FileResponse

    temp_dir = tempfile.mkdtemp()
    backup_path = Path(temp_dir) / "sessionguard_backup.db"

    conn = get_connection()
    try:
        conn.execute(f"VACUUM INTO '{backup_path}'")
    finally:
        conn.close()

    return FileResponse(
        path=str(backup_path),
        filename="sessionguard_backup.db",
        media_type="application/x-sqlite3"
    )


_EXPECTED_TABLES = {
    "sessions", "events", "users", "projects", "jobs",
    "live_runs", "ocr_results", "insights", "alerts", "audit_log",
}


@router.post("/restore")
async def restore_database(
    file: UploadFile = File(...),
    authorization: Optional[str] = Header(None),
):
    """Restore the database from an uploaded SQLite backup snapshot.

    The uploaded file is validated before any swap happens:
      1. must be a readable SQLite database,
      2. must pass an integrity check,
      3. must contain the expected core tables.

    If validation passes, the current database is first copied to a safety
    backup alongside it, then atomically replaced by the uploaded snapshot.
    """
    await _require_admin(authorization)

    if not file.filename or not file.filename.lower().endswith(".db"):
        raise HTTPException(status_code=400, detail="Upload a .db SQLite backup file.")

    # Stream the upload to a temp file so the client is fully consumed before
    # we touch the live database.
    upload_tmp = Path(tempfile.mkdtemp(prefix="sg_restore_")) / "upload.db"
    try:
        with upload_tmp.open("wb") as out:
            while chunk := await file.read(1024 * 1024):
                out.write(chunk)
    except Exception:
        raise HTTPException(status_code=400, detail="Failed to read uploaded file.")
    finally:
        await file.close()

    if upload_tmp.stat().st_size == 0:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    # Validate: readable SQLite + integrity + expected schema.
    try:
        conn = sqlite3.connect(str(upload_tmp))
        try:
            integrity = conn.execute("PRAGMA integrity_check").fetchone()[0]
            if integrity != "ok":
                raise HTTPException(status_code=400, detail=f"SQLite integrity check failed: {integrity}")
            tables = {
                row[0] for row in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                )
            }
            missing = _EXPECTED_TABLES - tables
            if missing:
                raise HTTPException(
                    status_code=400,
                    detail=f"Not a SessionGuard backup — missing tables: {', '.join(sorted(missing))}"
                )
        finally:
            conn.close()
    except sqlite3.DatabaseError:
        raise HTTPException(status_code=400, detail="Uploaded file is not a valid SQLite database.")

    DB_PATH = db_module.DB_PATH
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    # Safety backup of the current database before replacing it.
    safety = DB_PATH.with_suffix(f".pre-restore-{int(time.time())}.db")
    try:
        cur = get_connection()
        try:
            cur.execute(f"VACUUM INTO '{safety}'")
        finally:
            cur.close()
    except sqlite3.Error:
        safety = None

    # Atomic swap: copy into place then replace on same filesystem.
    staging = DB_PATH.with_suffix(".db.restore-staging")
    try:
        staging.write_bytes(upload_tmp.read_bytes())
        staging.replace(DB_PATH)
    except OSError as exc:
        raise HTTPException(status_code=500, detail=f"Restore failed while replacing database: {exc}")

    # Drop stale WAL/SHM sidecars left by the pre-restore database so they are
    # not replayed against the restored snapshot.
    for suffix in ("-wal", "-shm"):
        sidecar = Path(f"{DB_PATH}{suffix}")
        if sidecar.exists():
            try:
                sidecar.unlink()
            except OSError:
                pass

    return {
        "restored": True,
        "safety_backup": str(safety) if safety else None,
    }



import os, hmac, hashlib

def compute_audit_hmac(row: dict) -> str:
    """Compute HMAC-SHA256 signature for audit log tamper verification."""
    secret = os.getenv("SECRET_KEY", "sg-audit-signing-key")
    raw = f"{row.get('id')}:{row.get('user_id')}:{row.get('action')}:{row.get('created_at')}"
    return hmac.new(secret.encode("utf-8"), raw.encode("utf-8"), hashlib.sha256).hexdigest()


@router.get("/audit/export")
async def export_audit_log(
    format: str = Query("json", pattern="^(json|csv)$"),
    authorization: Optional[str] = Header(None),
    limit: int = Query(500, le=5000),
):
    """Export security audit log as CSV or JSON with HMAC-SHA256 signatures."""
    await _require_admin(authorization)
    raw_rows = await async_fetch_all(
        "SELECT a.id, a.user_id, u.email, u.username, a.action, a.resource, "
        "a.detail, a.ip_address, a.created_at "
        "FROM audit_log a LEFT JOIN users u ON u.id = a.user_id "
        "ORDER BY a.created_at DESC LIMIT ?", (limit,)
    )

    signed_rows = []
    for r in raw_rows:
        row_dict = dict(r)
        row_dict["hmac_signature"] = compute_audit_hmac(row_dict)
        signed_rows.append(row_dict)

    if format == "csv":
        import io
        import csv
        from fastapi.responses import StreamingResponse

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["id", "user_id", "email", "username", "action", "resource", "detail", "ip_address", "created_at", "hmac_signature"])
        for r in signed_rows:
            writer.writerow([r["id"], r["user_id"], r["email"], r["username"], r["action"], r["resource"], r["detail"], r["ip_address"], r["created_at"], r["hmac_signature"]])

        output.seek(0)
        return StreamingResponse(
            io.BytesIO(output.getvalue().encode("utf-8")),
            media_type="text/csv",
            headers={"Content-Disposition": 'attachment; filename="security_audit_log.csv"'}
        )

    return {"count": len(signed_rows), "records": signed_rows}

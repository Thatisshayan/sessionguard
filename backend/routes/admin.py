"""
backend/routes/admin.py
------------------------
Admin-only endpoints for system health, user management, audit log.

Maturity: Working Prototype
Future:   Add system metrics dashboard, quota management, org controls (V14).
"""

from fastapi import APIRouter, HTTPException, Header, Query
from pydantic import BaseModel
from typing import Optional
from database.db import get_connection
from backend.auth.service import get_current_user_from_token, hash_password

router = APIRouter(tags=["admin"])


def _require_admin(authorization: str | None) -> dict:
    user = get_current_user_from_token(authorization)
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required.")
    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin access required.")
    return user


# ── System health ─────────────────────────────────────────────────────────────

@router.get("/health")
def system_health(authorization: Optional[str] = Header(None)):
    """Full system health — DB stats, table counts, engine status."""
    _require_admin(authorization)
    conn   = get_connection()
    tables = [r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()]

    counts = {}
    for t in tables:
        try:
            counts[t] = conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
        except Exception:
            counts[t] = -1
    conn.close()

    from engines.video_pipeline import check_ffmpeg
    from engines.ocr_engine import check_ocr_status
    ffmpeg = check_ffmpeg()
    ocr    = check_ocr_status()

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
def system_stats(authorization: Optional[str] = Header(None)):
    """Platform-wide statistics."""
    _require_admin(authorization)
    conn = get_connection()
    r = conn.execute("""
        SELECT
            (SELECT COUNT(*) FROM sessions)      AS sessions,
            (SELECT COUNT(*) FROM events)        AS events,
            (SELECT COUNT(*) FROM users)         AS users,
            (SELECT COUNT(*) FROM projects)      AS projects,
            (SELECT COUNT(*) FROM review_items WHERE status='pending') AS pending_reviews,
            (SELECT COUNT(*) FROM alerts WHERE acknowledged=0) AS unacked_alerts,
            (SELECT COUNT(*) FROM jobs WHERE status='running') AS running_jobs,
            (SELECT COUNT(*) FROM exports)       AS exports
    """).fetchone()
    conn.close()
    return dict(r)


# ── User management ───────────────────────────────────────────────────────────

@router.get("/users")
def list_all_users(
    authorization: Optional[str] = Header(None),
    limit: int = Query(100, le=500),
):
    _require_admin(authorization)
    conn = get_connection()
    rows = conn.execute(
        "SELECT id, email, username, role, is_active, created_at, last_login "
        "FROM users ORDER BY created_at DESC LIMIT ?", (limit,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


class UserRoleUpdate(BaseModel):
    role:      Optional[str] = None
    is_active: Optional[bool] = None


@router.patch("/users/{user_id}")
def update_user(user_id: int, body: UserRoleUpdate,
                authorization: Optional[str] = Header(None)):
    admin = _require_admin(authorization)
    updates = {k: v for k, v in body.dict().items() if v is not None}
    if not updates:
        return {"message": "Nothing to update."}
    conn = get_connection()
    if not conn.execute("SELECT id FROM users WHERE id=?", (user_id,)).fetchone():
        conn.close()
        raise HTTPException(status_code=404, detail="User not found.")
    set_clause = ", ".join(f"{k}=?" for k in updates)
    conn.execute(f"UPDATE users SET {set_clause} WHERE id=?",
                 [*updates.values(), user_id])
    conn.commit(); conn.close()
    return {"user_id": user_id, "updated": list(updates.keys())}


@router.delete("/users/{user_id}", status_code=204)
def delete_user(user_id: int, authorization: Optional[str] = Header(None)):
    admin = _require_admin(authorization)
    if admin["user_id"] == user_id:
        raise HTTPException(status_code=400, detail="Cannot delete your own account.")
    conn = get_connection()
    cur  = conn.execute("DELETE FROM users WHERE id=?", (user_id,))
    conn.commit(); conn.close()
    if cur.rowcount == 0:
        raise HTTPException(status_code=404, detail="User not found.")


# ── Audit log ─────────────────────────────────────────────────────────────────

@router.get("/audit")
def audit_log(
    authorization: Optional[str] = Header(None),
    user_id: Optional[int] = Query(None),
    action:  Optional[str] = Query(None),
    limit:   int           = Query(100, le=500),
):
    _require_admin(authorization)
    conn    = get_connection()
    filters = []
    params  : list = []
    if user_id: filters.append("a.user_id=?"); params.append(user_id)
    if action:  filters.append("a.action LIKE ?"); params.append(f"%{action}%")
    where = ("WHERE " + " AND ".join(filters)) if filters else ""
    rows = conn.execute(
        f"SELECT a.*, u.email, u.username FROM audit_log a "
        f"LEFT JOIN users u ON u.id = a.user_id "
        f"{where} ORDER BY a.created_at DESC LIMIT ?",
        [*params, limit]
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]

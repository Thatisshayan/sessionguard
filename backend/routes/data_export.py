"""
backend/routes/data_export.py
------------------------------
Full database export for migration and backup.
GET /data-export/dump  → JSON dump of all tables
GET /data-export/backup → SQLite .db file download
Maturity: Working Prototype
"""

from fastapi import APIRouter, HTTPException, Header
from fastapi.responses import FileResponse, JSONResponse
from typing import Optional
import json
from pathlib import Path
from database.db import get_connection, get_db_path, async_fetch_all
from backend.auth.service import get_current_user_from_token

router = APIRouter(tags=["data-export"])

SKIP_TABLES = {"refresh_tokens", "audit_log"}  # sensitive / noisy


def _require_admin(authorization):
    user = get_current_user_from_token(authorization)
    if not user or user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin access required.")
    return user


@router.get("/data-export/dump")
async def dump_all(authorization: Optional[str] = Header(None)):
    """Export all session/event/insight data as JSON. Excludes auth tokens."""
    _require_admin(authorization)
    tables_row = await async_fetch_all(
        "SELECT name FROM sqlite_master WHERE type='table'"
    )
    tables = [r[0] for r in tables_row]
    result = {}
    for t in tables:
        if t in SKIP_TABLES or t == "sqlite_sequence":
            continue
        rows = await async_fetch_all(f"SELECT * FROM {t}")
        result[t] = rows
    return JSONResponse(content={"tables": list(result.keys()), "data": result})


@router.get("/data-export/backup")
def download_backup(authorization: Optional[str] = Header(None)):
    """Download the raw SQLite .db file."""
    _require_admin(authorization)
    try:
        db_path = get_db_path()
    except Exception:
        # Fallback — locate the file
        db_path = str(Path(__file__).resolve().parent.parent.parent / "config" / "sessionguard.db")

    p = Path(db_path)
    if not p.exists():
        raise HTTPException(status_code=404, detail="Database file not found.")
    return FileResponse(
        str(p),
        filename="sessionguard_backup.db",
        media_type="application/octet-stream",
    )

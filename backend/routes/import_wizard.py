"""
backend/routes/import_wizard.py - V14 Session Import Wizard
Original: ChatGPT | Reviewed + integrated: Claude
"""
import asyncio
import json, shutil, uuid, logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional
from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel, Field
from database.db import get_connection, async_fetch_one, async_fetch_all, async_execute
from engines.csv_import_engine import import_csv, preview_csv

log = logging.getLogger(__name__)

router = APIRouter(prefix="/import", tags=["import-wizard"])

PROJECT_ROOT     = Path(__file__).resolve().parents[2]
IMPORT_STORAGE   = PROJECT_ROOT / "storage" / "imports"
MANIFEST_PATH    = IMPORT_STORAGE / "manifest.json"


class ColumnMapping(BaseModel):
    date:         str = Field(..., min_length=1)
    bet:          str = Field(..., min_length=1)
    win:          str = Field(..., min_length=1)
    balance:      str = Field(..., min_length=1)
    spin_number:  Optional[str] = None


class ConfirmImportRequest(BaseModel):
    upload_id:     str = Field(..., min_length=1)
    column_mapping: ColumnMapping


def _ensure() -> None:
    IMPORT_STORAGE.mkdir(parents=True, exist_ok=True)
    if not MANIFEST_PATH.exists():
        MANIFEST_PATH.write_text("{}", encoding="utf-8")


def _load_manifest() -> Dict[str, Any]:
    _ensure()
    try: return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    except: return {}


def _save_manifest(m: Dict[str, Any]) -> None:
    _ensure()
    MANIFEST_PATH.write_text(json.dumps(m, indent=2), encoding="utf-8")


def _safe_name(name: str) -> str:
    c = "".join(ch if ch.isalnum() or ch in {".", "-", "_"} else "_" for ch in name)
    return c.strip("._") or "session_import.csv"


def _register(file_path: Path, original: str) -> str:
    uid = uuid.uuid4().hex
    m   = _load_manifest()
    m[uid] = {"file_path": str(file_path), "original_filename": original, "created_at": datetime.now(timezone.utc).isoformat()}
    _save_manifest(m)
    return uid


def _get_file(upload_id: str) -> Path:
    m   = _load_manifest()
    rec = m.get(upload_id)
    if not rec: raise HTTPException(404, "Upload ID not found. Preview the CSV again.")
    fp = Path(rec.get("file_path", ""))
    if not fp.exists(): raise HTTPException(404, "Uploaded file no longer available.")
    try: fp.resolve().relative_to(IMPORT_STORAGE.resolve())
    except ValueError: raise HTTPException(400, "Upload path is outside import storage.")
    return fp


def _create_session() -> str:
    sid  = uuid.uuid4().hex
    now  = datetime.now(timezone.utc).isoformat()
    name = f"CSV Import {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    conn = get_connection()
    try:
        cols = {r[1]: r for r in conn.execute("PRAGMA table_info(sessions)").fetchall()}
        vals: Dict[str, Any] = {}
        if "id" in cols:          vals["id"] = sid
        if "name" in cols:        vals["name"] = name
        if "status" in cols:      vals["status"] = "imported"
        if "created_at" in cols:  vals["created_at"] = now
        if "updated_at" in cols:  vals["updated_at"] = now
        if "event_count" in cols: vals["event_count"] = 0
        if not vals: raise RuntimeError("sessions table has no compatible columns.")
        ks = list(vals.keys())
        conn.execute(f"INSERT INTO sessions ({','.join(ks)}) VALUES ({','.join('?'*len(ks))})", [vals[k] for k in ks])
        conn.commit()
        return sid
    except Exception as e:
        conn.rollback(); raise HTTPException(500, f"Failed to create session: {e}")
    finally: conn.close()


@router.post("/preview")
async def preview_import(file: UploadFile = File(...)) -> Dict[str, Any]:
    """Upload a CSV, store it, return columns + preview rows + suggested mapping."""
    _ensure()
    safe     = _safe_name(file.filename or "import.csv")
    fp       = IMPORT_STORAGE / f"{uuid.uuid4().hex}_{safe}"
    try:
        with fp.open("wb") as dst: shutil.copyfileobj(file.file, dst)
    finally: await file.close()
    try: preview = preview_csv(fp)
    except Exception as e:
        fp.unlink(missing_ok=True)
        raise HTTPException(400, f"CSV preview failed: {e}")
    uid = _register(fp, file.filename or "import.csv")
    return {"upload_id": uid, "columns": preview.get("columns", []), "preview_rows": preview.get("preview_rows", []), "suggested_mapping": preview.get("suggested_mapping", {})}


@router.post("/confirm")
async def confirm_import(payload: ConfirmImportRequest) -> Dict[str, Any]:
    """Apply the column mapping, create a session, insert events, return counts."""
    fp         = _get_file(payload.upload_id)
    session_id = await asyncio.to_thread(_create_session)
    result     = await asyncio.to_thread(import_csv, fp, payload.column_mapping.model_dump(exclude_none=True), session_id)
    imported   = int(result.get("imported", 0))
    # Update event_count
    try:
        cols_row = await async_fetch_all("PRAGMA table_info(sessions)")
        cols = {r[1] for r in cols_row}
        if "event_count" in cols:
            await async_execute("UPDATE sessions SET event_count=? WHERE id=?", (imported, session_id))
    except Exception as e:
        log.warning("event_count_update_failed", session_id=session_id, error=str(e))
    return {"session_id": session_id, "event_count": imported, "skipped": int(result.get("skipped",0)), "warnings": result.get("warnings",[])}

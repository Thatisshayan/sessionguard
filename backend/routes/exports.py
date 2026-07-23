"""
backend/routes/exports.py
--------------------------
Export generation. All four formats now working end to end.
PDF and Excel: real styled documents via export_service.
JSON: inline data dump.
CSV: sessions table as CSV.

Maturity: Working Prototype — all formats implemented.
Future:   Evidence package builder (V7), streaming download (V9).
"""

import asyncio
import json
import csv
import io
from datetime import datetime
from pathlib import Path
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel
from typing import Optional
from database.db import get_connection, async_fetch_one, async_fetch_all, async_execute
from engines.analysis_engine import get_session_metrics, get_global_metrics
from backend.services.export_service import generate_pdf, generate_excel

router = APIRouter(tags=["exports"])

BASE_DIR    = Path(__file__).resolve().parent.parent.parent
EXPORTS_DIR = BASE_DIR / "storage" / "exports"
EXPORTS_DIR.mkdir(parents=True, exist_ok=True)


class ExportRequest(BaseModel):
    format:     str                 # json | pdf | excel | csv
    session_id: Optional[int] = None


@router.post("")
async def create_export(body: ExportRequest):
    """
    Generate an export artifact.
    All four formats (JSON, PDF, Excel, CSV) are fully implemented.
    """
    fmt = body.format.lower()
    if fmt not in {"json", "pdf", "excel", "csv"}:
        raise HTTPException(status_code=400,
                            detail="Format must be: json | pdf | excel | csv")

    ts    = datetime.now().strftime("%Y%m%d_%H%M%S")
    label = f"session_{body.session_id}" if body.session_id else "global"

    # ── PDF ───────────────────────────────────────────────────────────────────
    if fmt == "pdf":
        result = await asyncio.to_thread(generate_pdf, body.session_id)
        if not result["success"]:
            raise HTTPException(status_code=500, detail=result["error"])
        return {
            "format":    "pdf",
            "filename":  result["filename"],
            "file_path": result["file_path"],
            "export_id": result["export_id"],
            "status":    "complete",
        }

    # ── Excel ─────────────────────────────────────────────────────────────────
    if fmt == "excel":
        result = await asyncio.to_thread(generate_excel, body.session_id)
        if not result["success"]:
            raise HTTPException(status_code=500, detail=result["error"])
        return {
            "format":    "excel",
            "filename":  result["filename"],
            "file_path": result["file_path"],
            "export_id": result["export_id"],
            "status":    "complete",
        }

    # ── JSON ──────────────────────────────────────────────────────────────────
    if fmt == "json":
        data = await asyncio.to_thread(
            get_session_metrics, body.session_id
        ) if body.session_id else await asyncio.to_thread(get_global_metrics)
        if not data:
            raise HTTPException(status_code=404, detail="Session not found.")

        filename  = f"export_{label}_{ts}.json"
        filepath  = EXPORTS_DIR / filename
        with filepath.open("w") as f:
            json.dump({"exported_at": datetime.now().isoformat(), "data": data},
                      f, indent=2)

        export_id = await async_execute(
            "INSERT INTO exports (session_id, format, file_path) VALUES (?, 'json', ?)",
            (body.session_id, str(filepath))
        )
        return {
            "format": "json", "filename": filename,
            "file_path": str(filepath), "export_id": export_id, "status": "complete",
        }

    # ── CSV ───────────────────────────────────────────────────────────────────
    if fmt == "csv":
        if body.session_id:
            rows = await async_fetch_all(
                "SELECT * FROM sessions WHERE id=?", (body.session_id,)
            )
        else:
            rows = await async_fetch_all(
                "SELECT * FROM sessions ORDER BY date DESC"
            )

        if not rows:
            raise HTTPException(status_code=404, detail="No sessions found.")

        filename = f"export_{label}_{ts}.csv"
        filepath = EXPORTS_DIR / filename
        with filepath.open("w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=dict(rows[0]).keys())
            writer.writeheader()
            for row in rows:
                writer.writerow(dict(row))

        export_id = await async_execute(
            "INSERT INTO exports (session_id, format, file_path) VALUES (?, 'csv', ?)",
            (body.session_id, str(filepath))
        )
        return {
            "format": "csv", "filename": filename,
            "file_path": str(filepath), "export_id": export_id, "status": "complete",
        }


@router.get("")
async def list_exports(session_id: Optional[int] = None):
    """Return export history."""
    if session_id:
        rows = await async_fetch_all(
            "SELECT * FROM exports WHERE session_id=? ORDER BY created_at DESC",
            (session_id,)
        )
    else:
        rows = await async_fetch_all(
            "SELECT * FROM exports ORDER BY created_at DESC LIMIT 200"
        )
    return rows


@router.get("/{export_id}/download")
async def download_export(export_id: int):
    """Stream the export file directly to the client."""
    row = await async_fetch_one("SELECT * FROM exports WHERE id=?", (export_id,))
    if not row:
        raise HTTPException(status_code=404, detail="Export not found.")

    file_path = Path(row["file_path"])
    if not file_path.exists():
        raise HTTPException(status_code=410, detail="Export file has been deleted.")

    media_map = {
        "pdf":   "application/pdf",
        "excel": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "json":  "application/json",
        "csv":   "text/csv",
    }
    media_type = media_map.get(row["format"], "application/octet-stream")
    return FileResponse(
        str(file_path),
        filename=file_path.name,
        media_type=media_type,
    )

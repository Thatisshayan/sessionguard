"""
backend/routes/evidence.py
---------------------------
Evidence package generation endpoint.
Maturity: Working Prototype
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pathlib import Path
from backend.services.evidence_package import build_evidence_package

router = APIRouter(tags=["evidence"])


@router.post("/{session_id}/evidence")
def create_evidence_package(session_id: int):
    """
    Generate a complete evidence package ZIP for a session.
    Contains: PDF report + events CSV + insights + alerts + OCR results + frame thumbnails.
    """
    result = build_evidence_package(session_id)
    if not result["success"]:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@router.get("/{session_id}/evidence/{export_id}/download")
def download_evidence(session_id: int, export_id: int):
    """Stream the evidence package ZIP to the client."""
    from database.db import get_connection
    conn = get_connection()
    row  = conn.execute(
        "SELECT * FROM exports WHERE id=? AND session_id=?", (export_id, session_id)
    ).fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="Evidence package not found.")
    p = Path(row["file_path"])
    if not p.exists():
        raise HTTPException(status_code=410, detail="File no longer exists.")
    return FileResponse(
        str(p), filename=p.name,
        media_type="application/zip",
    )

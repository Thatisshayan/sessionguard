"""
backend/routes/evidence.py
---------------------------
Evidence package generation endpoint.
Maturity: Working Prototype
"""

from fastapi import APIRouter, HTTPException, Header
from fastapi.responses import FileResponse
import zipfile
from pathlib import Path
from backend.services.evidence_package import build_evidence_package, verify_evidence_manifest
from backend.auth.access import require_session_access

router = APIRouter(tags=["evidence"])


@router.post("/{session_id}/evidence")
async def create_evidence_package(session_id: int, authorization: str | None = Header(None)):
    """
    Generate a complete evidence package ZIP for a session.
    Contains: PDF report + events CSV + insights + alerts + OCR results + frame thumbnails.
    """
    await require_session_access(session_id, authorization)
    result = build_evidence_package(session_id)
    if not result["success"]:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@router.get("/{session_id}/evidence/{export_id}/download")
async def download_evidence(session_id: int, export_id: int, authorization: str | None = Header(None)):
    """Stream the evidence package ZIP to the client."""
    await require_session_access(session_id, authorization)
    from database.db import async_fetch_one
    row = await async_fetch_one(
        "SELECT * FROM exports WHERE id=? AND session_id=?", (export_id, session_id)
    )
    if not row:
        raise HTTPException(status_code=404, detail="Evidence package not found.")
    p = Path(row["file_path"])
    if not p.exists():
        raise HTTPException(status_code=410, detail="File no longer exists.")
    return FileResponse(
        str(p), filename=p.name,
        media_type="application/zip",
    )


@router.get("/{session_id}/evidence/verify")
async def verify_evidence(session_id: int, authorization: str | None = Header(None)):
    """
    Verify SHA-256 manifest integrity for an evidence package.
    Returns per-file status (ok/tampered/not_found).
    """
    await require_session_access(session_id, authorization)
    from database.db import async_fetch_one
    row = await async_fetch_one(
        "SELECT file_path FROM exports WHERE session_id=? AND format='evidence' ORDER BY created_at DESC LIMIT 1",
        (session_id,)
    )

    if not row:
        raise HTTPException(status_code=404, detail="No evidence package found for session.")

    zip_path = row["file_path"]
    if not zipfile.is_zipfile(zip_path):
        raise HTTPException(status_code=400, detail="File is not a valid ZIP.")

    result = verify_evidence_manifest(zip_path)
    return {"session_id": session_id, "manifest_verified": result}

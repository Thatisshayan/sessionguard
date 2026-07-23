"""
backend/routes/notes.py
------------------------
Session notes with full version history.
Every update creates a new version rather than overwriting.
Maturity: Working Prototype
"""

from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel
from typing import Optional
from database.db import get_connection, async_fetch_one, async_fetch_all, async_execute
from backend.auth.service import get_current_user_from_token

router = APIRouter(tags=["notes"])


class NoteCreate(BaseModel):
    note: str


@router.get("/{session_id}/notes")
async def list_notes(session_id: int):
    """Return all note versions for a session, newest first."""
    rows = await async_fetch_all(
        "SELECT n.*, u.username FROM session_notes n "
        "LEFT JOIN users u ON u.id = n.user_id "
        "WHERE n.session_id=? ORDER BY n.version DESC",
        (session_id,)
    )
    return rows


@router.post("/{session_id}/notes", status_code=201)
async def add_note(
    session_id: int,
    body:       NoteCreate,
    authorization: Optional[str] = Header(None),
):
    """Add a note version to a session."""
    user    = get_current_user_from_token(authorization)
    user_id = user["user_id"] if user else None

    # Check session exists
    if not await async_fetch_one("SELECT id FROM sessions WHERE id=?", (session_id,)):
        raise HTTPException(status_code=404, detail="Session not found.")

    # Get next version
    last_row = await async_fetch_one(
        "SELECT MAX(version) AS max_ver FROM session_notes WHERE session_id=?", (session_id,)
    )
    version = (last_row["max_ver"] if last_row else 0) + 1

    note_id = await async_execute(
        "INSERT INTO session_notes (session_id, user_id, note, version) VALUES (?,?,?,?)",
        (session_id, user_id, body.note, version)
    )

    return {
        "id":         note_id,
        "session_id": session_id,
        "version":    version,
        "note":       body.note,
        "user_id":    user_id,
    }


@router.get("/{session_id}/notes/latest")
async def latest_note(session_id: int):
    """Return only the most recent note version."""
    row = await async_fetch_one(
        "SELECT n.*, u.username FROM session_notes n "
        "LEFT JOIN users u ON u.id = n.user_id "
        "WHERE n.session_id=? ORDER BY n.version DESC LIMIT 1",
        (session_id,)
    )
    if not row:
        return {"session_id": session_id, "note": None, "version": 0}
    return dict(row)

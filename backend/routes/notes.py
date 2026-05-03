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
from database.db import get_connection
from backend.auth.service import get_current_user_from_token

router = APIRouter(tags=["notes"])


class NoteCreate(BaseModel):
    note: str


@router.get("/{session_id}/notes")
def list_notes(session_id: int):
    """Return all note versions for a session, newest first."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT n.*, u.username FROM session_notes n "
        "LEFT JOIN users u ON u.id = n.user_id "
        "WHERE n.session_id=? ORDER BY n.version DESC",
        (session_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


@router.post("/{session_id}/notes", status_code=201)
def add_note(
    session_id: int,
    body:       NoteCreate,
    authorization: Optional[str] = Header(None),
):
    """Add a note version to a session."""
    user    = get_current_user_from_token(authorization)
    user_id = user["user_id"] if user else None

    conn = get_connection()
    # Check session exists
    if not conn.execute("SELECT id FROM sessions WHERE id=?", (session_id,)).fetchone():
        conn.close()
        raise HTTPException(status_code=404, detail="Session not found.")

    # Get next version
    last = conn.execute(
        "SELECT MAX(version) FROM session_notes WHERE session_id=?", (session_id,)
    ).fetchone()[0]
    version = (last or 0) + 1

    cur = conn.execute(
        "INSERT INTO session_notes (session_id, user_id, note, version) VALUES (?,?,?,?)",
        (session_id, user_id, body.note, version)
    )
    note_id = cur.lastrowid
    conn.commit()
    conn.close()

    return {
        "id":         note_id,
        "session_id": session_id,
        "version":    version,
        "note":       body.note,
        "user_id":    user_id,
    }


@router.get("/{session_id}/notes/latest")
def latest_note(session_id: int):
    """Return only the most recent note version."""
    conn = get_connection()
    row  = conn.execute(
        "SELECT n.*, u.username FROM session_notes n "
        "LEFT JOIN users u ON u.id = n.user_id "
        "WHERE n.session_id=? ORDER BY n.version DESC LIMIT 1",
        (session_id,)
    ).fetchone()
    conn.close()
    if not row:
        return {"session_id": session_id, "note": None, "version": 0}
    return dict(row)

"""
backend/routes/tags.py
-----------------------
V11: Session tags and threaded comments.
Maturity: Working Prototype
"""

from fastapi import APIRouter, HTTPException, Header, Query
from pydantic import BaseModel
from typing import Optional
from database.db import get_connection
from backend.auth.service import get_current_user_from_token

router = APIRouter(tags=["tags"])


# ── Tags ──────────────────────────────────────────────────────────────────────

@router.post("/sessions/{session_id}/tags")
def add_tag(session_id: int, body: dict,
            authorization: Optional[str] = Header(None)):
    tag = (body.get("tag") or "").strip().lower()[:30]
    if not tag:
        raise HTTPException(status_code=400, detail="Tag cannot be empty.")
    conn = get_connection()
    try:
        conn.execute("INSERT OR IGNORE INTO session_tags (session_id, tag) VALUES (?,?)",
                     (session_id, tag))
        conn.commit()
    except Exception as e:
        conn.close()
        raise HTTPException(status_code=400, detail=str(e))
    conn.close()
    return {"session_id": session_id, "tag": tag, "added": True}


@router.get("/sessions/{session_id}/tags")
def get_tags(session_id: int):
    conn = get_connection()
    rows = conn.execute("SELECT tag, created_at FROM session_tags WHERE session_id=?",
                        (session_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


@router.delete("/sessions/{session_id}/tags/{tag}", status_code=204)
def remove_tag(session_id: int, tag: str):
    conn = get_connection()
    conn.execute("DELETE FROM session_tags WHERE session_id=? AND tag=?",
                 (session_id, tag.lower()))
    conn.commit()
    conn.close()


@router.get("/tags/all")
def all_tags(limit: int = Query(50, le=200)):
    """Return all unique tags across all sessions with counts."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT tag, COUNT(*) as count FROM session_tags GROUP BY tag ORDER BY count DESC LIMIT ?",
        (limit,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


@router.get("/tags/{tag}/sessions")
def sessions_with_tag(tag: str, limit: int = Query(50, le=200)):
    """Return all sessions with a given tag."""
    conn = get_connection()
    rows = conn.execute("""
        SELECT s.id, s.name, s.game_name, s.date, s.rtp, s.net_result, s.status
        FROM session_tags st JOIN sessions s ON s.id = st.session_id
        WHERE st.tag=? ORDER BY s.date DESC LIMIT ?
    """, (tag.lower(), limit)).fetchall()
    conn.close()
    return {"tag": tag, "sessions": [dict(r) for r in rows]}


# ── Comments ──────────────────────────────────────────────────────────────────

class CommentCreate(BaseModel):
    body:      str
    parent_id: Optional[int] = None


@router.get("/sessions/{session_id}/comments")
def get_comments(session_id: int):
    conn = get_connection()
    rows = conn.execute("""
        SELECT c.*, u.username FROM session_comments c
        LEFT JOIN users u ON u.id = c.user_id
        WHERE c.session_id=? ORDER BY c.created_at ASC
    """, (session_id,)).fetchall()
    conn.close()
    comments = [dict(r) for r in rows]
    # Nest replies under parents
    top_level = [c for c in comments if not c["parent_id"]]
    for c in top_level:
        c["replies"] = [r for r in comments if r["parent_id"] == c["id"]]
    return top_level


@router.post("/sessions/{session_id}/comments", status_code=201)
def add_comment(session_id: int, body: CommentCreate,
                authorization: Optional[str] = Header(None)):
    user    = get_current_user_from_token(authorization)
    user_id = user["user_id"] if user else None
    if not body.body.strip():
        raise HTTPException(status_code=400, detail="Comment cannot be empty.")
    conn = get_connection()
    cur  = conn.execute(
        "INSERT INTO session_comments (session_id, user_id, parent_id, body) VALUES (?,?,?,?)",
        (session_id, user_id, body.parent_id, body.body.strip())
    )
    comment_id = cur.lastrowid
    conn.commit()
    conn.close()
    return {"id": comment_id, "session_id": session_id, "body": body.body}


@router.delete("/sessions/{session_id}/comments/{comment_id}", status_code=204)
def delete_comment(session_id: int, comment_id: int,
                   authorization: Optional[str] = Header(None)):
    user = get_current_user_from_token(authorization)
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required.")
    conn = get_connection()
    c = conn.execute("SELECT user_id FROM session_comments WHERE id=?",
                     (comment_id,)).fetchone()
    if not c:
        conn.close()
        raise HTTPException(status_code=404, detail="Comment not found.")
    if c["user_id"] != user["user_id"] and user["role"] != "admin":
        conn.close()
        raise HTTPException(status_code=403, detail="Cannot delete another user's comment.")
    conn.execute("DELETE FROM session_comments WHERE id=?", (comment_id,))
    conn.commit()
    conn.close()

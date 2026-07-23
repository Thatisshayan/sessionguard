"""
backend/routes/tags.py
-----------------------
V11: Session tags and threaded comments.
Maturity: Working Prototype
"""

from fastapi import APIRouter, HTTPException, Header, Query
from pydantic import BaseModel
from typing import Optional
from database.db import get_connection, async_fetch_one, async_fetch_all, async_execute
from backend.auth.service import get_current_user_from_token

router = APIRouter(tags=["tags"])


# ── Tags ──────────────────────────────────────────────────────────────────────

@router.post("/sessions/{session_id}/tags")
async def add_tag(session_id: int, body: dict,
            authorization: Optional[str] = Header(None)):
    tag = (body.get("tag") or "").strip().lower()[:30]
    if not tag:
        raise HTTPException(status_code=400, detail="Tag cannot be empty.")
    try:
        await async_execute("INSERT OR IGNORE INTO session_tags (session_id, tag) VALUES (?,?)",
                     (session_id, tag))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"session_id": session_id, "tag": tag, "added": True}


@router.get("/sessions/{session_id}/tags")
async def get_tags(session_id: int):
    rows = await async_fetch_all("SELECT tag, created_at FROM session_tags WHERE session_id=?",
                        (session_id,))
    return rows


@router.delete("/sessions/{session_id}/tags/{tag}", status_code=204)
async def remove_tag(session_id: int, tag: str):
    await async_execute("DELETE FROM session_tags WHERE session_id=? AND tag=?",
                 (session_id, tag.lower()))


@router.get("/tags/all")
async def all_tags(limit: int = Query(50, le=200)):
    """Return all unique tags across all sessions with counts."""
    rows = await async_fetch_all(
        "SELECT tag, COUNT(*) as count FROM session_tags GROUP BY tag ORDER BY count DESC LIMIT ?",
        (limit,)
    )
    return rows


@router.get("/tags/{tag}/sessions")
async def sessions_with_tag(tag: str, limit: int = Query(50, le=200)):
    """Return all sessions with a given tag."""
    rows = await async_fetch_all("""
        SELECT s.id, s.name, s.game_name, s.date, s.rtp, s.net_result, s.status
        FROM session_tags st JOIN sessions s ON s.id = st.session_id
        WHERE st.tag=? ORDER BY s.date DESC LIMIT ?
    """, (tag.lower(), limit))
    return {"tag": tag, "sessions": rows}


# ── Comments ──────────────────────────────────────────────────────────────────

class CommentCreate(BaseModel):
    body:      str
    parent_id: Optional[int] = None


@router.get("/sessions/{session_id}/comments")
async def get_comments(session_id: int):
    rows = await async_fetch_all("""
        SELECT c.*, u.username FROM session_comments c
        LEFT JOIN users u ON u.id = c.user_id
        WHERE c.session_id=? ORDER BY c.created_at ASC
    """, (session_id,))
    comments = [dict(r) for r in rows]
    # Nest replies under parents
    top_level = [c for c in comments if not c["parent_id"]]
    for c in top_level:
        c["replies"] = [r for r in comments if r["parent_id"] == c["id"]]
    return top_level


@router.post("/sessions/{session_id}/comments", status_code=201)
async def add_comment(session_id: int, body: CommentCreate,
                authorization: Optional[str] = Header(None)):
    user    = get_current_user_from_token(authorization)
    user_id = user["user_id"] if user else None
    if not body.body.strip():
        raise HTTPException(status_code=400, detail="Comment cannot be empty.")
    comment_id = await async_execute(
        "INSERT INTO session_comments (session_id, user_id, parent_id, body) VALUES (?,?,?,?)",
        (session_id, user_id, body.parent_id, body.body.strip())
    )
    return {"id": comment_id, "session_id": session_id, "body": body.body}


@router.delete("/sessions/{session_id}/comments/{comment_id}", status_code=204)
async def delete_comment(session_id: int, comment_id: int,
                   authorization: Optional[str] = Header(None)):
    user = get_current_user_from_token(authorization)
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required.")
    c = await async_fetch_one("SELECT user_id FROM session_comments WHERE id=?",
                     (comment_id,))
    if not c:
        raise HTTPException(status_code=404, detail="Comment not found.")
    if c["user_id"] != user["user_id"] and user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Cannot delete another user's comment.")
    await async_execute("DELETE FROM session_comments WHERE id=?", (comment_id,))

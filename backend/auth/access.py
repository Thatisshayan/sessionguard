"""Session-level authorization helpers."""

from fastapi import HTTPException

from backend.auth.service import get_current_user_from_token
from database.db import async_fetch_one


def require_current_user(authorization: str | None) -> dict:
    user = get_current_user_from_token(authorization)
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required.")
    return user


def require_admin(authorization: str | None) -> dict:
    user = require_current_user(authorization)
    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin access required.")
    return user


async def require_session_access(session_id: int, authorization: str | None) -> dict:
    """
    Require that the caller can access a session.

    Admins always pass. Non-admin users must own the session or have access to
    a project that contains it.
    """
    user = require_current_user(authorization)
    if user["role"] == "admin":
        return user

    session = await async_fetch_one(
        "SELECT id, owner_id FROM sessions WHERE id=?",
        (session_id,)
    )
    if not session:
        raise HTTPException(status_code=404, detail="Session not found.")

    if session.get("owner_id") == user["user_id"]:
        return user

    project_link = await async_fetch_one(
        """
        SELECT 1
        FROM session_projects sp
        JOIN project_members pm ON pm.project_id = sp.project_id
        WHERE sp.session_id=? AND pm.user_id=?
        LIMIT 1
        """,
        (session_id, user["user_id"]),
    )
    if project_link:
        return user

    raise HTTPException(status_code=403, detail="Insufficient session access.")

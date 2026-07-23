"""
backend/routes/projects.py
---------------------------
Projects CRUD + membership management.
Projects group sessions under a named workspace.

Maturity: Working Prototype
Future:   Shared team access, project-level exports, timeline view (V11).
"""

from fastapi import APIRouter, HTTPException, Header, Query
from pydantic import BaseModel
from typing import Optional
import json
from database.db import get_connection, async_fetch_one, async_fetch_all, async_execute
from backend.auth.service import get_current_user_from_token

router = APIRouter(tags=["projects"])


class ProjectCreate(BaseModel):
    name:        str
    description: str = ""
    tags:        list[str] = []


class ProjectUpdate(BaseModel):
    name:        Optional[str] = None
    description: Optional[str] = None
    tags:        Optional[list[str]] = None


class AddMemberRequest(BaseModel):
    user_id: int
    role:    str = "viewer"   # viewer | editor | admin


class LinkSessionRequest(BaseModel):
    session_id: int


def _require_auth(authorization: str | None) -> dict:
    user = get_current_user_from_token(authorization)
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required.")
    return user


def _require_project_access(project_id: int, user_id: int, min_role: str = "viewer") -> dict:
    conn = get_connection()
    p = conn.execute("SELECT * FROM projects WHERE id=?", (project_id,)).fetchone()
    if not p:
        conn.close()
        raise HTTPException(status_code=404, detail="Project not found.")

    if p["owner_id"] == user_id:
        conn.close()
        return dict(p)

    member = conn.execute(
        "SELECT role FROM project_members WHERE project_id=? AND user_id=?",
        (project_id, user_id)
    ).fetchone()
    conn.close()

    role_hierarchy = {"viewer": 0, "editor": 1, "admin": 2}
    if not member or role_hierarchy.get(member["role"], -1) < role_hierarchy.get(min_role, 0):
        raise HTTPException(status_code=403, detail="Insufficient project permissions.")
    return dict(p)


# ── CRUD ──────────────────────────────────────────────────────────────────────

@router.get("")
async def list_projects(authorization: Optional[str] = Header(None)):
    """Return all projects the current user owns or is a member of."""
    user = _require_auth(authorization)
    rows = await async_fetch_all("""
        SELECT DISTINCT p.*, u.username AS owner_name
        FROM projects p
        JOIN users u ON u.id = p.owner_id
        LEFT JOIN project_members pm ON pm.project_id = p.id
        WHERE p.owner_id=? OR pm.user_id=?
        ORDER BY p.updated_at DESC
    """, (user["user_id"], user["user_id"]))
    result = []
    for r in rows:
        d = dict(r)
        d["tags"] = json.loads(d.get("tags") or "[]")
        result.append(d)
    return result


@router.post("", status_code=201)
async def create_project(body: ProjectCreate, authorization: Optional[str] = Header(None)):
    user = _require_auth(authorization)
    project_id = await async_execute(
        "INSERT INTO projects (name, description, owner_id, tags) VALUES (?,?,?,?)",
        (body.name, body.description, user["user_id"], json.dumps(body.tags))
    )
    return {"id": project_id, "name": body.name, "owner_id": user["user_id"]}


@router.get("/{project_id}")
async def get_project(project_id: int, authorization: Optional[str] = Header(None)):
    user = _require_auth(authorization)
    p    = _require_project_access(project_id, user["user_id"])
    # Attach sessions and members
    sessions = await async_fetch_all("""
        SELECT s.id, s.name, s.game_name, s.date, s.net_result, s.rtp, s.status
        FROM sessions s
        JOIN session_projects sp ON sp.session_id = s.id
        WHERE sp.project_id=?
        ORDER BY s.date DESC
    """, (project_id,))
    members = await async_fetch_all("""
        SELECT u.id, u.username, u.email, pm.role, pm.joined_at
        FROM project_members pm
        JOIN users u ON u.id = pm.user_id
        WHERE pm.project_id=?
    """, (project_id,))
    p["tags"]     = json.loads(p.get("tags") or "[]")
    p["sessions"] = sessions
    p["members"]  = members
    return p


@router.patch("/{project_id}")
async def update_project(project_id: int, body: ProjectUpdate, authorization: Optional[str] = Header(None)):
    user = _require_auth(authorization)
    _require_project_access(project_id, user["user_id"], min_role="editor")
    updates = {k: v for k, v in body.dict().items() if v is not None}
    if not updates:
        return {"message": "Nothing to update."}
    if "tags" in updates:
        updates["tags"] = json.dumps(updates["tags"])
    set_clause = ", ".join(f"{k}=?" for k in updates)
    set_clause += ", updated_at=datetime('now')"
    params = list(updates.values())
    await async_execute(f"UPDATE projects SET {set_clause} WHERE id=?", (*params, project_id))
    return {"id": project_id, "updated": list(updates.keys())}


@router.delete("/{project_id}", status_code=204)
async def delete_project(project_id: int, authorization: Optional[str] = Header(None)):
    user = _require_auth(authorization)
    p = await async_fetch_one("SELECT owner_id FROM projects WHERE id=?", (project_id,))
    if not p:
        raise HTTPException(status_code=404, detail="Project not found.")
    if p["owner_id"] != user["user_id"] and user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Only project owner can delete.")
    await async_execute("DELETE FROM projects WHERE id=?", (project_id,))


# ── Sessions ──────────────────────────────────────────────────────────────────

@router.post("/{project_id}/sessions")
async def add_session_to_project(project_id: int, body: LinkSessionRequest,
                            authorization: Optional[str] = Header(None)):
    user = _require_auth(authorization)
    _require_project_access(project_id, user["user_id"], min_role="editor")
    try:
        await async_execute("INSERT OR IGNORE INTO session_projects (session_id, project_id) VALUES (?,?)",
                     (body.session_id, project_id))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"project_id": project_id, "session_id": body.session_id, "linked": True}


@router.delete("/{project_id}/sessions/{session_id}", status_code=204)
async def remove_session_from_project(project_id: int, session_id: int,
                                 authorization: Optional[str] = Header(None)):
    user = _require_auth(authorization)
    _require_project_access(project_id, user["user_id"], min_role="editor")
    await async_execute("DELETE FROM session_projects WHERE project_id=? AND session_id=?",
                 (project_id, session_id))


# ── Members ───────────────────────────────────────────────────────────────────

@router.post("/{project_id}/members")
async def add_member(project_id: int, body: AddMemberRequest,
               authorization: Optional[str] = Header(None)):
    user = _require_auth(authorization)
    _require_project_access(project_id, user["user_id"], min_role="admin")
    try:
        await async_execute(
            "INSERT OR REPLACE INTO project_members (project_id, user_id, role) VALUES (?,?,?)",
            (project_id, body.user_id, body.role)
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"project_id": project_id, "user_id": body.user_id, "role": body.role}


@router.delete("/{project_id}/members/{user_id}", status_code=204)
async def remove_member(project_id: int, user_id: int,
                  authorization: Optional[str] = Header(None)):
    user = _require_auth(authorization)
    _require_project_access(project_id, user["user_id"], min_role="admin")
    await async_execute("DELETE FROM project_members WHERE project_id=? AND user_id=?",
                 (project_id, user_id))

"""
backend/routes/profiles.py
---------------------------
Parser profile CRUD. Profiles hold per-game OCR ROI configs and alert thresholds.
"""

import json
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from database.db import get_connection

router = APIRouter(tags=["profiles"])


class ProfileCreate(BaseModel):
    name:        str
    game_name:   str
    platform:    str
    roi_config:  Optional[dict] = {}
    alert_rules: Optional[dict] = {}


@router.get("")
def list_profiles():
    conn = get_connection()
    rows = conn.execute("SELECT * FROM profiles ORDER BY name").fetchall()
    conn.close()
    result = []
    for r in rows:
        d = dict(r)
        d["roi_config"]  = json.loads(d["roi_config"]  or "{}")
        d["alert_rules"] = json.loads(d["alert_rules"] or "{}")
        result.append(d)
    return result


@router.get("/{profile_id}")
def get_profile(profile_id: int):
    conn = get_connection()
    row = conn.execute("SELECT * FROM profiles WHERE id = ?", (profile_id,)).fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="Profile not found.")
    d = dict(row)
    d["roi_config"]  = json.loads(d["roi_config"]  or "{}")
    d["alert_rules"] = json.loads(d["alert_rules"] or "{}")
    return d


@router.post("", status_code=201)
def create_profile(body: ProfileCreate):
    conn = get_connection()
    try:
        cur = conn.execute(
            "INSERT INTO profiles (name, game_name, platform, roi_config, alert_rules) "
            "VALUES (?, ?, ?, ?, ?)",
            (body.name, body.game_name, body.platform,
             json.dumps(body.roi_config), json.dumps(body.alert_rules))
        )
        profile_id = cur.lastrowid
        conn.commit()
    except Exception as e:
        conn.close()
        raise HTTPException(status_code=409, detail=f"Profile name already exists: {e}")
    conn.close()
    return {"id": profile_id, **body.dict()}


@router.delete("/{profile_id}", status_code=204)
def delete_profile(profile_id: int):
    conn = get_connection()
    cur = conn.execute("DELETE FROM profiles WHERE id = ?", (profile_id,))
    conn.commit()
    conn.close()
    if cur.rowcount == 0:
        raise HTTPException(status_code=404, detail="Profile not found.")


@router.patch("/{profile_id}")
def update_profile(profile_id: int, body: dict):
    """Update a profile in place — preserves ID and linked OCR results."""
    import json
    from fastapi import Request
    conn = get_connection()
    existing = conn.execute("SELECT * FROM profiles WHERE id=?", (profile_id,)).fetchone()
    if not existing:
        conn.close()
        raise HTTPException(status_code=404, detail="Profile not found.")

    allowed = {'name', 'game_name', 'platform', 'roi_config', 'alert_rules'}
    updates = {k: v for k, v in body.items() if k in allowed}
    if not updates:
        conn.close()
        return {"id": profile_id, "message": "Nothing to update."}

    # Serialize dict fields
    for key in ('roi_config', 'alert_rules'):
        if key in updates and isinstance(updates[key], dict):
            updates[key] = json.dumps(updates[key])

    set_clause = ", ".join(f"{k}=?" for k in updates)
    conn.execute(f"UPDATE profiles SET {set_clause} WHERE id=?",
                 [*updates.values(), profile_id])
    conn.commit()
    conn.close()
    return {"id": profile_id, "updated": list(updates.keys())}

"""
backend/routes/profiles.py
---------------------------
Parser profile CRUD. Profiles hold per-game OCR ROI configs and alert thresholds.
"""

import json
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from database.db import get_connection, async_fetch_one, async_fetch_all, async_execute

router = APIRouter(tags=["profiles"])


class ProfileCreate(BaseModel):
    name:        str
    game_name:   str
    platform:    str
    roi_config:  Optional[dict] = {}
    alert_rules: Optional[dict] = {}


@router.get("")
async def list_profiles():
    rows = await async_fetch_all("SELECT * FROM profiles ORDER BY name")
    result = []
    for r in rows:
        d = dict(r)
        d["roi_config"]  = json.loads(d["roi_config"]  or "{}")
        d["alert_rules"] = json.loads(d["alert_rules"] or "{}")
        result.append(d)
    return result


@router.get("/{profile_id}")
async def get_profile(profile_id: int):
    row = await async_fetch_one("SELECT * FROM profiles WHERE id = ?", (profile_id,))
    if not row:
        raise HTTPException(status_code=404, detail="Profile not found.")
    d = dict(row)
    d["roi_config"]  = json.loads(d["roi_config"]  or "{}")
    d["alert_rules"] = json.loads(d["alert_rules"] or "{}")
    return d


@router.post("", status_code=201)
async def create_profile(body: ProfileCreate):
    try:
        profile_id = await async_execute(
            "INSERT INTO profiles (name, game_name, platform, roi_config, alert_rules) "
            "VALUES (?, ?, ?, ?, ?)",
            (body.name, body.game_name, body.platform,
             json.dumps(body.roi_config), json.dumps(body.alert_rules))
        )
    except Exception as e:
        raise HTTPException(status_code=409, detail=f"Profile name already exists: {e}")
    return {"id": profile_id, **body.dict()}


@router.delete("/{profile_id}", status_code=204)
async def delete_profile(profile_id: int):
    rowcount = await async_execute("DELETE FROM profiles WHERE id = ?", (profile_id,))
    if rowcount == 0:
        raise HTTPException(status_code=404, detail="Profile not found.")


@router.patch("/{profile_id}")
async def update_profile(profile_id: int, body: dict):
    """Update a profile in place — preserves ID and linked OCR results."""
    import json
    existing = await async_fetch_one("SELECT * FROM profiles WHERE id=?", (profile_id,))
    if not existing:
        raise HTTPException(status_code=404, detail="Profile not found.")

    allowed = {'name', 'game_name', 'platform', 'roi_config', 'alert_rules'}
    updates = {k: v for k, v in body.items() if k in allowed}
    if not updates:
        return {"id": profile_id, "message": "Nothing to update."}

    # Serialize dict fields
    for key in ('roi_config', 'alert_rules'):
        if key in updates and isinstance(updates[key], dict):
            updates[key] = json.dumps(updates[key])

    set_clause = ", ".join(f"{k}=?" for k in updates)
    await async_execute(f"UPDATE profiles SET {set_clause} WHERE id=?",
                 (*updates.values(), profile_id))
    return {"id": profile_id, "updated": list(updates.keys())}

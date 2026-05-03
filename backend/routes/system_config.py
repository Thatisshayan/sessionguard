"""
backend/routes/system_config.py
---------------------------------
Read and update app_config.json from the browser.
Only admin users can write config. Validates known keys before saving.
Maturity: Working Prototype
"""

from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel
from typing import Optional, Any
import json
from pathlib import Path
from backend.auth.service import get_current_user_from_token

router  = APIRouter(tags=["system-config"])
CONFIG  = Path(__file__).resolve().parent.parent.parent / "config" / "app_config.json"

# Keys users are allowed to change — protect secret_key and database path
EDITABLE_KEYS = {
    "auth.access_token_expire_minutes",
    "thresholds.rtp_warning",
    "thresholds.rtp_critical",
    "thresholds.max_loss",
    "thresholds.streak_warning",
    "thresholds.streak_critical",
    "ocr.confidence_threshold",
    "ocr.scale",
    "ffmpeg.frame_extraction_fps",
    "workers.max_threads",
}


def _load() -> dict:
    try:
        return json.loads(CONFIG.read_text())
    except Exception:
        return {}


def _save(cfg: dict):
    CONFIG.write_text(json.dumps(cfg, indent=2))


def _get_nested(cfg: dict, key: str) -> Any:
    parts = key.split(".")
    obj   = cfg
    for p in parts:
        if not isinstance(obj, dict) or p not in obj:
            return None
        obj = obj[p]
    return obj


def _set_nested(cfg: dict, key: str, value: Any):
    parts = key.split(".")
    obj   = cfg
    for p in parts[:-1]:
        obj = obj.setdefault(p, {})
    obj[parts[-1]] = value


@router.get("/system-config")
def get_config(authorization: Optional[str] = Header(None)):
    """Return the full app_config.json (auth required)."""
    user = get_current_user_from_token(authorization)
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required.")
    return _load()


class ConfigUpdate(BaseModel):
    key:   str
    value: Any


@router.patch("/system-config")
def update_config(body: ConfigUpdate, authorization: Optional[str] = Header(None)):
    """Update a single config key. Admin only. Only editable keys allowed."""
    user = get_current_user_from_token(authorization)
    if not user or user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin access required.")
    if body.key not in EDITABLE_KEYS:
        raise HTTPException(
            status_code=400,
            detail=f"Key '{body.key}' is not editable. Allowed: {sorted(EDITABLE_KEYS)}"
        )
    cfg = _load()
    _set_nested(cfg, body.key, body.value)
    _save(cfg)
    return {"key": body.key, "value": body.value, "saved": True}


@router.get("/system-config/editable-keys")
def editable_keys():
    """Return which keys are allowed to be edited."""
    cfg     = _load()
    result  = {}
    for key in sorted(EDITABLE_KEYS):
        result[key] = _get_nested(cfg, key)
    return result

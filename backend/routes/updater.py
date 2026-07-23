"""
backend/routes/updater.py — Auto-update checker.
Polls GitHub Releases API. No new dependencies.
"""
import json, logging, re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional
import requests
from fastapi import APIRouter
from pydantic import BaseModel
from database.db import get_connection

logger = logging.getLogger(__name__)
router = APIRouter(tags=["updater"])
PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH  = PROJECT_ROOT / "config" / "app_config.json"
DISMISSED_KEY = "dismissed_update_version"

def _read_config():
    try: return json.loads(CONFIG_PATH.read_text()) if CONFIG_PATH.exists() else {}
    except: return {}

def _safe(v, d=""): return str(v) if v is not None else d

def _norm(v):
    r = _safe(v).strip()
    return r[1:] if r.lower().startswith("v") else r

def _vtuple(v):
    c = _norm(v)
    if not c: return (0,0,0)
    main = re.split(r"[-+]", c, maxsplit=1)[0]
    parts = []
    for p in main.split("."):
        m = re.match(r"^(\d+)", p)
        parts.append(int(m.group(1)) if m else 0)
    while len(parts) < 3: parts.append(0)
    return tuple(parts[:3])

def _is_newer(latest, current): return _vtuple(latest) > _vtuple(current)

def _get_setting(key):
    try:
        conn = get_connection()
        row = conn.execute("SELECT value FROM system_settings WHERE key=? LIMIT 1", (key,)).fetchone()
        conn.close()
        return row["value"] if row else None
    except: return None

def _set_setting(key, value):
    try:
        conn = get_connection()
        conn.execute("INSERT OR REPLACE INTO system_settings (key,value) VALUES (?,?)", (key, value))
        conn.commit()
        conn.close()
        return True
    except: return False

def _github_url(cfg):
    gh = cfg.get("github") or {}
    owner = _safe(gh.get("owner")).strip()
    repo  = _safe(gh.get("repo")).strip()
    if not owner or not repo: return None
    tmpl = _safe(gh.get("releases_url"), "https://api.github.com/repos/{owner}/{repo}/releases/latest")
    return tmpl.replace("{owner}", owner).replace("{repo}", repo)

def _download_url(release):
    assets = release.get("assets") or []
    fallback = None
    for a in assets:
        if not isinstance(a, dict): continue
        url  = a.get("browser_download_url")
        name = _safe(a.get("name")).lower()
        if url and fallback is None: fallback = url
        if url and name.endswith((".exe", ".msi", ".zip")): return url
    return fallback or release.get("html_url")

@router.get("/updater/current-version")
def current_version():
    cfg = _read_config()
    return {"version": _safe(cfg.get("version"), "0.0.0"),
            "build_date": _safe(cfg.get("build_date"), datetime.now(timezone.utc).isoformat()),
            "changelog_url": _safe(cfg.get("changelog_url"))}

@router.get("/updater/check")
def check_for_update():
    cfg       = _read_config()
    current   = _safe(cfg.get("version"), "0.0.0")
    dismissed = _get_setting(DISMISSED_KEY)
    url       = _github_url(cfg)
    base = {"current_version": current, "latest_version": current, "update_available": False,
            "download_url": None, "release_url": None, "release_notes": "",
            "published_at": None, "dismissed_version": dismissed, "is_dismissed": False}
    if not url: return {**base, "error": "github_config_missing"}
    try:
        r = requests.get(url, headers={"Accept":"application/vnd.github+json",
            "User-Agent":"SessionGuard-Updater/1.0","X-GitHub-Api-Version":"2022-11-28"}, timeout=10)
        r.raise_for_status(); data = r.json()
        latest = _norm(data.get("tag_name")) or current
        avail  = _is_newer(latest, current)
        is_dismissed = bool(dismissed and _norm(dismissed) == _norm(latest))
        return {"current_version": current, "latest_version": latest, "update_available": avail,
                "download_url": _download_url(data), "release_url": _safe(data.get("html_url")),
                "release_notes": _safe(data.get("body")), "published_at": data.get("published_at"),
                "dismissed_version": dismissed, "is_dismissed": is_dismissed, "error": None}
    except requests.RequestException: return {**base, "error": "offline"}
    except: return {**base, "error": "unknown"}

class DismissRequest(BaseModel):
    version: str

@router.post("/updater/dismiss")
def dismiss_update(payload: DismissRequest):
    version = _norm(payload.version)
    if not version: return {"ok": False, "dismissed_version": None, "error": "missing_version"}
    saved = _set_setting(DISMISSED_KEY, version)
    return {"ok": saved, "dismissed_version": version if saved else None, "error": None if saved else "save_failed"}

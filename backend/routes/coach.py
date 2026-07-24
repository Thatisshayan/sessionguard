"""backend/routes/coach.py - Live coaching endpoint."""
from fastapi import APIRouter, Query, Header, HTTPException
from typing import Optional
from engines.live_coach_engine import get_coaching_message, reset_coach
from database.db import get_connection, async_fetch_all
from backend.auth.access import require_admin, require_session_access
import os, json
from pathlib import Path

router = APIRouter(tags=["coach"])


@router.get("/coach-status")
def coach_status():
    """Check if AI coaching is available. Separate path to avoid {run_id} conflict."""
    has_key = bool(os.getenv('NVIDIA_API_KEY', ''))
    if not has_key:
        try:
            cfg = json.loads((Path(__file__).resolve().parent.parent.parent / 'config' / 'app_config.json').read_text())
            has_key = bool(cfg.get('ai', {}).get('nvidia_api_key', ''))
        except Exception:
            pass
    return {
        "ai_available":       has_key,
        "fallback_available": True,
        "styles":             ['strict', 'balanced', 'supportive'],
        "message":            "NVIDIA AI coach active" if has_key else "Rule-based coach active — add NVIDIA_API_KEY for AI coaching",
    }


@router.get("/coach/{run_id}")
async def get_coach_message(
    run_id: int,
    style:  str  = Query('balanced'),
    force:  bool = Query(False),
    authorization: Optional[str] = Header(None, alias="Authorization"),
):
    conn = get_connection()
    run = conn.execute("SELECT session_id FROM live_runs WHERE id=?", (run_id,)).fetchone()
    conn.close()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found.")
    await require_session_access(run["session_id"], authorization)
    rows   = await async_fetch_all(
        "SELECT * FROM live_events WHERE run_id=? ORDER BY id DESC LIMIT 100",
        (run_id,)
    )
    events = list(reversed([dict(r) for r in rows]))
    msg    = get_coaching_message(events, style=style, force=force)
    return {"message": msg, "run_id": run_id, "event_count": len(events)}


@router.post("/coach/{run_id}/reset")
def reset_coach_state(run_id: int, authorization: Optional[str] = Header(None, alias="Authorization")):
    require_admin(authorization)
    reset_coach()
    return {"reset": True, "run_id": run_id}

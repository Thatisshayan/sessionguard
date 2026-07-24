"""
backend/routes/alerts.py
-------------------------
Alert retrieval, acknowledgement, and summary endpoints.
"""

from fastapi import APIRouter, HTTPException, Query, Header
from typing import Optional
from engines.alerts_engine import (
    get_alerts,
    acknowledge_alert,
    generate_and_persist_alerts,
    get_alert_summary,
)
from backend.auth.access import require_admin, require_session_access

router = APIRouter(tags=["alerts"])


@router.get("")
def list_alerts(
    session_id:          Optional[int]  = Query(None),
    unacknowledged_only: bool           = Query(False),
    authorization: Optional[str] = Header(None, alias="Authorization"),
):
    """Return alerts. Critical first. Optionally filter by session or status."""
    if session_id is not None:
        require_session_access(session_id, authorization)
    else:
        require_admin(authorization)
    return get_alerts(session_id=session_id, unacknowledged_only=unacknowledged_only)


@router.get("/summary")
def alert_summary(authorization: Optional[str] = Header(None, alias="Authorization")):
    """Return counts by severity for dashboard badges."""
    require_admin(authorization)
    return get_alert_summary()


@router.patch("/{alert_id}/acknowledge")
def acknowledge(alert_id: int, authorization: Optional[str] = Header(None, alias="Authorization")):
    """Mark an alert as acknowledged."""
    require_admin(authorization)
    success = acknowledge_alert(alert_id)
    if not success:
        raise HTTPException(status_code=404, detail="Alert not found.")
    return {"alert_id": alert_id, "acknowledged": True}


@router.post("/{session_id}/regenerate")
def regenerate_alerts(session_id: int, authorization: Optional[str] = Header(None, alias="Authorization")):
    """Re-run alert rules for a session. Replaces existing alerts."""
    require_session_access(session_id, authorization)
    results = generate_and_persist_alerts(session_id)
    if results is None:
        raise HTTPException(status_code=404, detail="Session not found.")
    return {"session_id": session_id, "generated": len(results), "alerts": results}


@router.get("/{alert_id}/explain")
def explain_alert(alert_id: int, authorization: Optional[str] = Header(None, alias="Authorization")):
    """
    Return AI-generated root cause explanation for an alert.
    Calls NVIDIA AI or Ollama with session context; falls back to rule-based.
    """
    from engines.alerts_engine import get_alerts
    from engines.ai_insights_engine import _build_session_summary, _call_claude, _get_api_key, SYSTEM_PROMPT
    from engines.offline_ai import is_ollama_available as _ollama_available, call_ollama_json as _ollama_call

    alerts = get_alerts()
    alert = next((a for a in alerts if a["id"] == alert_id), None)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found.")

    session_id = alert["session_id"]
    require_session_access(session_id, authorization)
    summary = _build_session_summary(session_id)

    explain_prompt = f"""You are a session analyst explaining why an alert fired.

ALERT DETAILS:
  Rule: {alert['rule']}
  Message: {alert['message']}
  Severity: {alert['severity']}
  Session: {alert['session_name']} ({alert['game_name']})
  Fired at: {alert['created_at']}

SESSION DATA:
{_format_summary(summary)}

Your task: Explain in 2-3 sentences WHY this alert likely fired. Be specific about the contributing factors from the session data. Use plain language. Do NOT suggest strategies to win.

Output JSON only:
{{"explanation": "Your explanation here (1-3 sentences)", "likely_causes": ["cause 1", "cause 2"], "confidence": "high|medium|low"}}
"""

    api_key = _get_api_key()

    if api_key:
        try:
            raw_text, _ = _call_claude(explain_prompt, api_key, system_prompt=SYSTEM_PROMPT)
            import json
            data = json.loads(raw_text)
            return {"alert_id": alert_id, "source": "nvidia_ai", "explanation": data}
        except Exception:
            pass

    if _ollama_available():
        try:
            result = _ollama_call(explain_prompt)
            if result and "error" not in result:
                return {"alert_id": alert_id, "source": "ollama", "explanation": result}
        except Exception:
            pass

    return {
        "alert_id": alert_id,
        "source": "rule_based",
        "explanation": {
            "explanation": f"This {alert['severity']} alert fired because {alert['message']}",
            "likely_causes": ["Review session data for contributing factors"],
            "confidence": "low"
        }
    }


def _format_summary(summary: dict) -> str:
    """Compact string formatting of session summary."""
    if not summary:
        return "No session data available."
    s = summary.get("session", {})
    ev = summary.get("events", {})
    bt = summary.get("bet_trend", {})
    bc = summary.get("balance_curve", [])
    return f"""
  Game: {s.get('game')} | Platform: {s.get('platform')} | Date: {s.get('date')}
  Duration: {s.get('duration_min', '?')} min | Spins: {s.get('spins', '?')}
  Net result: ${s.get('net_result', '?')} | RTP: {s.get('rtp', '?')}%
  Biggest win: ${s.get('biggest_win', '?')} | Losing streak: {s.get('losing_streak', '?')} spins
  Event stats: {ev.get('total', '?')} total, {ev.get('winning', '?')} winning, avg bet ${ev.get('avg_bet', '?')}
  Bet trend: early ${bt.get('early_avg', '?')} → late ${bt.get('late_avg', '?')}
  Balance curve: {bc}
"""

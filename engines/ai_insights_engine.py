"""
engines/ai_insights_engine.py
-------------------------------
V13 AI Layer — Claude-powered session analysis.

Replaces rule-based insight text with real Claude AI narrative.
Uses the Anthropic Messages API directly via urllib (stdlib — no extra deps).
Falls back to rule-based engine gracefully when no API key is set.

Model: claude-sonnet-4-6  ($3/$15 per million tokens)
Context sent: summarised session data only — never raw events (cost control).

Setup:
    Set ANTHROPIC_API_KEY in environment or config/app_config.json:
    export ANTHROPIC_API_KEY=sk-ant-...

Maturity: Working Prototype
Future:   Streaming responses (V14), prompt caching for repeated sessions (V14).
"""

from __future__ import annotations
import json
import os
import urllib.request
import urllib.error
from datetime import datetime
from pathlib import Path

from database.db import get_connection
from engines.offline_ai import is_ollama_available, call_ollama_json

# ── Config ────────────────────────────────────────────────────────────────────
_CONFIG_PATH = Path(__file__).resolve().parent.parent / "config" / "app_config.json"
API_URL      = "https://api.anthropic.com/v1/messages"
MODEL        = "claude-sonnet-4-6"
MAX_TOKENS   = 1024


def _get_api_key() -> str | None:
    """Load API key from environment first, then config file."""
    key = os.getenv("ANTHROPIC_API_KEY", "").strip()
    if key:
        return key
    try:
        cfg = json.loads(_CONFIG_PATH.read_text())
        return cfg.get("ai", {}).get("anthropic_api_key", "").strip() or None
    except Exception:
        return None


def is_available() -> bool:
    """True if an API key is configured."""
    return bool(_get_api_key())


# ── Data preparation (cost control) ───────────────────────────────────────────

def _build_session_summary(session_id: int) -> dict | None:
    """
    Build a compact summary of session data to send to Claude.
    We send stats, not raw events — keeps token usage low.
    """
    conn    = get_connection()
    session = conn.execute("SELECT * FROM sessions WHERE id=?", (session_id,)).fetchone()
    if not session:
        conn.close()
        return None

    s = dict(session)

    # Event stats
    ev_stats = conn.execute("""
        SELECT COUNT(*) AS total,
               COUNT(CASE WHEN win_amount > 0 THEN 1 END) AS winning,
               ROUND(AVG(bet_amount), 2) AS avg_bet,
               ROUND(MAX(win_amount), 2) AS biggest_win,
               ROUND(AVG(confidence_score), 3) AS avg_confidence
        FROM events WHERE session_id=?
    """, (session_id,)).fetchone()

    # Bet trajectory (first 5 vs last 5 avg)
    early_bets = conn.execute(
        "SELECT AVG(bet_amount) FROM (SELECT bet_amount FROM events WHERE session_id=? ORDER BY timestamp LIMIT 5)",
        (session_id,)
    ).fetchone()[0]
    late_bets  = conn.execute(
        "SELECT AVG(bet_amount) FROM (SELECT bet_amount FROM events WHERE session_id=? ORDER BY timestamp DESC LIMIT 5)",
        (session_id,)
    ).fetchone()[0]

    # Balance curve simplified (10 equally-spaced points)
    all_bals = [r[0] for r in conn.execute(
        "SELECT balance_after FROM events WHERE session_id=? ORDER BY timestamp",
        (session_id,)
    ).fetchall()]

    if len(all_bals) >= 10:
        step    = len(all_bals) // 10
        sampled = [round(all_bals[i * step], 2) for i in range(10)]
    else:
        sampled = [round(b, 2) for b in all_bals]

    # Existing rule-based insights (give Claude the context)
    insights = [dict(r) for r in conn.execute(
        "SELECT severity, text FROM insights WHERE session_id=? ORDER BY severity LIMIT 5",
        (session_id,)
    ).fetchall()]

    conn.close()

    return {
        "session": {
            "name":         s["name"],
            "game":         s["game_name"],
            "platform":     s["platform"],
            "date":         s["date"],
            "duration_min": s.get("duration_minutes"),
            "start_bal":    s.get("start_balance"),
            "end_bal":      s.get("end_balance"),
            "net_result":   s.get("net_result"),
            "rtp":          s.get("rtp"),
            "spins":        s.get("spins"),
            "total_wagered":s.get("total_bets"),
            "biggest_win":  s.get("biggest_win"),
            "losing_streak":s.get("losing_streak"),
            "status":       s.get("status"),
        },
        "events": dict(ev_stats) if ev_stats else {},
        "bet_trend": {
            "early_avg": round(early_bets or 0, 2),
            "late_avg":  round(late_bets  or 0, 2),
            "escalated": bool(late_bets and early_bets and late_bets > early_bets * 1.5),
        },
        "balance_curve": sampled,
        "existing_insights": [i["text"] for i in insights],
    }


# ── Prompt construction ────────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are SessionGuard's AI analysis engine. You analyse casino/slot session data and produce honest, useful insights for the player reviewing their own sessions.

IMPORTANT RULES:
1. You are a REVIEW and BEHAVIOUR tool — never suggest strategies to win or predict outcomes.
2. Be direct and specific. Use the actual numbers from the data.
3. Identify real patterns: tilt signals, escalation, recovery chasing, discipline issues.
4. Never be preachy. One sentence of context is enough — don't lecture.
5. Focus on what the player can actually learn from this session.
6. If the session shows healthy discipline, say so clearly — don't manufacture problems.
7. Use plain language. No jargon. No hedging.

Output format — respond with ONLY valid JSON, no markdown, no explanation outside the JSON:
{
  "headline": "One sentence summary of the most important finding (max 15 words)",
  "risk_level": "low|moderate|high|critical",
  "insights": [
    {
      "severity": "info|warning|critical",
      "category": "rtp|behaviour|discipline|variance|confidence",
      "text": "Specific finding using real numbers from the data"
    }
  ],
  "behaviour_summary": "2-3 sentences on the player's behaviour patterns this session",
  "notable_moments": ["specific moment from data worth highlighting"],
  "discipline_score": 0-100,
  "one_line_verdict": "Plain English verdict the player can act on"
}"""


def _build_user_prompt(summary: dict) -> str:
    s   = summary["session"]
    ev  = summary["events"]
    bt  = summary["bet_trend"]
    bc  = summary["balance_curve"]
    ins = summary["existing_insights"]

    return f"""Analyse this session:

GAME: {s['game']} on {s['platform']} — {s['date']}
DURATION: {s.get('duration_min', '?')} minutes | SPINS: {s.get('spins', '?')}

FINANCIALS:
  Start balance:  ${s.get('start_bal', '?')}
  End balance:    ${s.get('end_bal', '?')}
  Net result:     ${s.get('net_result', '?')}
  RTP:            {s.get('rtp', '?')}%
  Total wagered:  ${s.get('total_wagered', '?')}
  Biggest win:    ${s.get('biggest_win', '?')}
  Losing streak:  {s.get('losing_streak', '?')} spins

EVENT STATS:
  Total events:   {ev.get('total', '?')}
  Winning spins:  {ev.get('winning', '?')}
  Average bet:    ${ev.get('avg_bet', '?')}
  Biggest win:    ${ev.get('biggest_win', '?')}
  Avg confidence: {ev.get('avg_confidence', '?')} (OCR accuracy — 1.0 = perfect)

BET SIZING:
  Early session average: ${bt['early_avg']}
  Late session average:  ${bt['late_avg']}
  Escalation detected:   {bt['escalated']}

BALANCE CURVE (10 sample points across session):
  {bc}

EXISTING RULE-BASED INSIGHTS (for context):
  {chr(10).join(f'  - {i}' for i in ins) if ins else '  None'}

Produce the JSON analysis now."""


# ── API call ──────────────────────────────────────────────────────────────────

def _call_claude(prompt: str, api_key: str, system_prompt: str | None = None) -> str:
    """Make raw API call using urllib. Returns response text."""
    payload = json.dumps({
        "model":      MODEL,
        "max_tokens": MAX_TOKENS,
        "system":     system_prompt or SYSTEM_PROMPT,
        "messages": [
            {"role": "user", "content": prompt}
        ],
    }).encode()

    req = urllib.request.Request(
        API_URL,
        data=payload,
        headers={
            "Content-Type":   "application/json",
            "x-api-key":      api_key,
            "anthropic-version": "2023-06-01",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            body = json.loads(response.read())
            return body["content"][0]["text"]
    except urllib.error.HTTPError as e:
        error_body = e.read().decode()
        raise RuntimeError(f"Anthropic API error {e.code}: {error_body}")


# ── Fallback rule-based response ──────────────────────────────────────────────

def _fallback_analysis(session_id: int, summary: dict) -> dict:
    """Return rule-based analysis when no API key is set."""
    s   = summary["session"]
    rtp = float(s.get("rtp") or 0)
    net = float(s.get("net_result") or 0)
    streak = int(s.get("losing_streak") or 0)

    risk = "low"
    if rtp < 85 or streak > 15:  risk = "critical"
    elif rtp < 92 or streak > 8: risk = "high"
    elif rtp < 96 or net < -50:  risk = "moderate"

    return {
        "source":       "rule_based",
        "ai_available": False,
        "message":      "Add ANTHROPIC_API_KEY to enable Claude AI analysis.",
        "headline":     f"Session completed — RTP {rtp}%, net ${net:+.2f}",
        "risk_level":   risk,
        "discipline_score": max(0, min(100, int(rtp - 10))),
        "one_line_verdict": (
            "Session within normal parameters." if risk == "low"
            else f"RTP {rtp}% and {streak}-spin losing streak warrant review."
        ),
        "insights": [{"severity": "info", "category": "rtp",
                       "text": i} for i in summary.get("existing_insights", [])[:3]],
        "behaviour_summary": "Rule-based analysis only. Set ANTHROPIC_API_KEY for AI-powered insights.",
        "notable_moments": [],
    }


# ── Main public function ──────────────────────────────────────────────────────

def analyse_session_with_ai(session_id: int) -> dict:
    """
    Run Claude AI analysis on a session.
    Falls back to rule-based if no API key configured.
    Persists result to insights table.
    """
    summary = _build_session_summary(session_id)
    if not summary:
        return {"error": f"Session {session_id} not found."}

    api_key = _get_api_key()

    if not api_key:
        # Try Ollama before rule-based fallback
        if is_ollama_available():
            try:
                from engines.prompt_manager import get_active_prompt
                active = get_active_prompt("session_analysis")
                system_prompt = active["system_prompt"] if active else None
                prompt = _build_user_prompt(summary)

                ollama_result = call_ollama_json(
                    prompt,
                    model="llama3.2:latest",
                    system_prompt=system_prompt or SYSTEM_PROMPT,
                )

                if "error" not in ollama_result:
                    from backend.schemas.ai import parse_ai_response
                    try:
                        import json as _json
                        response = parse_ai_response(_json.dumps(ollama_result) if isinstance(ollama_result, dict) else ollama_result)
                        analysis = response.model_dump()
                    except Exception:
                        analysis = ollama_result

                    analysis["source"] = "ollama_ai"
                    analysis["model"] = "llama3.2:latest"
                    analysis["ai_available"] = True
                    analysis["session_id"] = session_id
                    analysis["generated_at"] = datetime.now().isoformat()
                    _persist_ai_insights(session_id, analysis)
                    return analysis
            except Exception:
                pass  # Fall through to rule-based

        result = _fallback_analysis(session_id, summary)
        result["session_id"] = session_id
        return result

    try:
        from engines.prompt_manager import get_active_prompt
        active = get_active_prompt("session_analysis")
        system_prompt = active["system_prompt"] if active else None
        prompt      = _build_user_prompt(summary)
        raw_text    = _call_claude(prompt, api_key, system_prompt=system_prompt)

        from backend.schemas.ai import parse_ai_response
        response = parse_ai_response(raw_text)
        analysis = response.model_dump()
        analysis["source"]       = "claude_ai"
        analysis["model"]        = MODEL
        analysis["ai_available"] = True
        analysis["session_id"]   = session_id
        analysis["generated_at"] = datetime.now().isoformat()

        # Persist top insights back to insights table
        _persist_ai_insights(session_id, analysis)

        return analysis

    except json.JSONDecodeError as e:
        return {
            "source":    "claude_ai",
            "ai_available": True,
            "session_id": session_id,
            "error":     f"Could not parse AI response: {e}",
            "raw":       raw_text[:500] if 'raw_text' in dir() else "",
        }
    except Exception as e:
        # Fall back to rule-based on any error
        result = _fallback_analysis(session_id, summary)
        result["session_id"]  = session_id
        result["ai_error"]    = str(e)
        return result


def _persist_ai_insights(session_id: int, analysis: dict):
    """Save AI-generated insights to the insights table."""
    if not analysis.get("insights"):
        return
    conn = get_connection()
    # Remove any old AI insights for this session
    conn.execute(
        "DELETE FROM insights WHERE session_id=? AND text LIKE '[AI]%'",
        (session_id,)
    )
    for ins in analysis.get("insights", [])[:5]:
        conn.execute(
            "INSERT INTO insights (session_id, severity, text) VALUES (?,?,?)",
            (session_id, ins.get("severity", "info"),
             f"[AI] {ins.get('text', '')}")
        )
    conn.commit()
    conn.close()



def get_ai_status() -> dict:
    """Return AI layer availability and cache stats."""
    conn = get_connection()
    cached = conn.execute("SELECT COUNT(*), SUM(tokens_used) FROM ai_insights").fetchone()
    conn.close()
    return {
        "available":        _api_available(),
        "has_library":      _HAS_ANTHROPIC,
        "has_api_key":      bool(os.getenv("ANTHROPIC_API_KEY")),
        "model":            MODEL,
        "cached_responses": cached[0] or 0,
        "total_tokens":     cached[1] or 0,
        "install_cmd":      "pip install anthropic" if not _HAS_ANTHROPIC else None,
        "key_env_var":      "ANTHROPIC_API_KEY",
        "console_url":      "https://console.anthropic.com",
        "message": (
            f"Claude AI active — model {MODEL}" if _api_available()
            else "Fallback mode active — set ANTHROPIC_API_KEY to enable Claude AI."
        ),
    }


# ── Aliases for route compatibility ───────────────────────────────────────────


def get_ai_status() -> dict:
    """Return AI layer availability and cache stats."""
    try:
        import anthropic as _anth
        has_lib = True
    except ImportError:
        has_lib = False
    conn = get_connection()
    cached = conn.execute("SELECT COUNT(*), SUM(tokens_used) FROM ai_insights").fetchone()
    conn.close()
    avail = is_available()
    return {
        "available":        avail,
        "has_library":      has_lib,
        "has_api_key":      bool(os.getenv("ANTHROPIC_API_KEY")),
        "model":            MODEL,
        "cached_responses": cached[0] or 0,
        "total_tokens":     cached[1] or 0,
        "install_cmd":      "pip install anthropic" if not has_lib else None,
        "key_env_var":      "ANTHROPIC_API_KEY",
        "console_url":      "https://console.anthropic.com",
        "message": (
            f"Claude AI active — model {MODEL}" if avail
            else "Fallback mode — set ANTHROPIC_API_KEY to enable Claude AI."
        ),
    }
# ── Aliases for route compatibility ───────────────────────────────────────────
_api_available            = is_available
generate_session_narrative = analyse_session_with_ai


def generate_comparison_narrative(session_ids: list) -> dict:
    """Generate AI comparison narrative across sessions."""
    conn = get_connection()
    sessions = [dict(r) for r in conn.execute(
        f"SELECT * FROM sessions WHERE id IN ({','.join('?'*len(session_ids))})",
        session_ids
    ).fetchall()]
    conn.close()
    if len(sessions) < 2: return {"error": "Need at least 2 sessions.", "source": "error"}
    api_key = _get_api_key()
    data = [{"name": s["name"], "game": s["game_name"], "rtp": s["rtp"],
             "net": s["net_result"], "spins": s["spins"]} for s in sessions]
    import json as _json
    prompt = f"Compare these {len(sessions)} sessions in 3-4 sentences, focusing on behaviour patterns:\n{_json.dumps(data, indent=2)}"
    if api_key:
        result = _call_claude(prompt, api_key)
        if result: return {"content": result, "source": "claude", "model": MODEL}
    best = max(sessions, key=lambda x: float(x["rtp"] or 0))
    worst = min(sessions, key=lambda x: float(x["rtp"] or 0))
    fallback = (f"Compared {len(sessions)} sessions. Best RTP: {best['game_name']} at {best['rtp']}%. "
                f"Worst RTP: {worst['game_name']} at {worst['rtp']}%. "
                f"Net spread: ${round(float(best['net_result'] or 0) - float(worst['net_result'] or 0), 2)}")
    return {"content": fallback, "source": "rule_based"}


def suggest_review_resolution(review_item_id: int) -> dict:
    """Suggest accept/reject for a review item."""
    conn = get_connection()
    item = conn.execute(
        "SELECT ri.*, e.bet_amount, e.win_amount, e.confidence_score "
        "FROM review_items ri LEFT JOIN events e ON e.id=ri.event_id WHERE ri.id=?",
        (review_item_id,)
    ).fetchone()
    conn.close()
    if not item: return {"error": "Review item not found.", "source": "error"}
    conf = float(item["confidence_score"] or 0)
    if conf >= 0.85: return {"suggestion": "accept", "confidence": conf, "reasoning": f"OCR confidence {conf:.0%} above threshold.", "source": "rule_based"}
    if conf >= 0.70: return {"suggestion": "accept", "confidence": round(conf-0.1, 2), "reasoning": f"Borderline confidence {conf:.0%} — accept with caution.", "source": "rule_based"}
    return {"suggestion": "reject", "confidence": round(1-conf, 2), "reasoning": f"Low confidence {conf:.0%} — likely OCR misread.", "source": "rule_based"}

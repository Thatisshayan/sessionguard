"""
engines/insights_engine.py
---------------------------
Generates human-readable insight objects from session data.
Rule-based now. AI-assisted text in V13+.

Maturity: Working Prototype
Future:   Replace rule text with LLM-generated narrative summaries (V13).
"""

from database.db import get_connection


def get_insights(session_id: int | None = None, limit: int = 50) -> list:
    """
    Return persisted insights. If session_id given, filter to that session.
    Ordered by severity: critical first, then warning, then info.
    """
    conn = get_connection()

    severity_order = "CASE severity WHEN 'critical' THEN 0 WHEN 'warning' THEN 1 ELSE 2 END"

    if session_id:
        rows = conn.execute(
            f"SELECT i.*, s.name AS session_name, s.game_name "
            f"FROM insights i JOIN sessions s ON s.id = i.session_id "
            f"WHERE i.session_id = ? "
            f"ORDER BY {severity_order}, i.created_at DESC LIMIT ?",
            (session_id, limit)
        ).fetchall()
    else:
        rows = conn.execute(
            f"SELECT i.*, s.name AS session_name, s.game_name "
            f"FROM insights i JOIN sessions s ON s.id = i.session_id "
            f"ORDER BY {severity_order}, i.created_at DESC LIMIT ?",
            (limit,)
        ).fetchall()

    conn.close()

    return [
        {
            "id":           r["id"],
            "session_id":   r["session_id"],
            "session_name": r["session_name"],
            "game_name":    r["game_name"],
            "category":     r["category"],
            "severity":     r["severity"],
            "text":         r["text"],
            "created_at":   r["created_at"],
        }
        for r in rows
    ]


def generate_and_persist_insights(session_id: int) -> list:
    """
    Re-run insight rules for a session and persist results.
    Clears existing insights for session first to avoid duplication.
    Called after a new session is created or updated.
    """
    conn = get_connection()

    s = conn.execute("SELECT * FROM sessions WHERE id = ?", (session_id,)).fetchone()
    if not s:
        conn.close()
        return []

    conn.execute("DELETE FROM insights WHERE session_id = ?", (session_id,))

    new_insights = []

    # ── RTP classification ────────────────────────────────────────────────────
    if s["rtp"] < 85:
        new_insights.append(dict(
            session_id=session_id, category="performance", severity="critical",
            text=f"RTP of {s['rtp']}% is critically low. "
                 f"Net loss of ${abs(s['net_result']):.2f} over {s['spins']} spins detected."))
    elif s["rtp"] < 96:
        new_insights.append(dict(
            session_id=session_id, category="performance", severity="warning",
            text=f"RTP of {s['rtp']}% is below the expected average of 96%. "
                 f"Net result: ${s['net_result']:.2f}."))
    else:
        new_insights.append(dict(
            session_id=session_id, category="performance", severity="info",
            text=f"Above-average session — RTP {s['rtp']}%, "
                 f"net result ${s['net_result']:.2f} over {s['spins']} spins."))

    # ── Losing streak ─────────────────────────────────────────────────────────
    if s["losing_streak"] > 15:
        new_insights.append(dict(
            session_id=session_id, category="risk", severity="critical",
            text=f"A losing streak of {s['losing_streak']} consecutive spins was detected. "
                 f"This is a significant high-variance event."))
    elif s["losing_streak"] > 8:
        new_insights.append(dict(
            session_id=session_id, category="risk", severity="warning",
            text=f"Moderate losing streak of {s['losing_streak']} spins — "
                 f"elevated drawdown risk in this period."))

    # ── Big win ───────────────────────────────────────────────────────────────
    if s["biggest_win"] > s["total_bets"] * 0.25:
        new_insights.append(dict(
            session_id=session_id, category="behavior", severity="info",
            text=f"A single win of ${s['biggest_win']:.2f} represented over 25% of total "
                 f"wagers. Sessions with large outlier wins can skew RTP readings."))

    # ── Short session flag ────────────────────────────────────────────────────
    if s["duration_minutes"] < 20 and s["net_result"] < -100:
        new_insights.append(dict(
            session_id=session_id, category="behavior", severity="warning",
            text=f"Large loss (${abs(s['net_result']):.2f}) in a short {s['duration_minutes']}-minute "
                 f"session may indicate impulsive play or high bet sizing."))

    # ── Persist ───────────────────────────────────────────────────────────────
    for ins in new_insights:
        conn.execute(
            "INSERT INTO insights (session_id, category, severity, text) "
            "VALUES (:session_id, :category, :severity, :text)", ins)

    conn.commit()
    conn.close()
    return new_insights

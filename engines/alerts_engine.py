"""
engines/alerts_engine.py
-------------------------
Threshold-based alert generation from session data.
Rules are defined here, not in routes.

Maturity: Working Prototype
Future:   Load thresholds from profile alert_rules JSON (per-game config).
          Add real-time alert triggering in V8.
"""

from database.db import get_connection


# ── Default thresholds (overridden per-profile in V7+) ───────────────────────
THRESHOLDS = {
    "rtp_warning":     96.0,
    "rtp_critical":    85.0,
    "max_loss":        200.0,
    "streak_warning":  8,
    "streak_critical": 15,
}


def get_alerts(session_id: int | None = None, unacknowledged_only: bool = False, alert_id: int | None = None) -> list:
    """
    Return alerts from DB. Optionally filter by session, acknowledged state, or alert id.
    Critical alerts first.
    """
    conn = get_connection()

    severity_order = "CASE severity WHEN 'critical' THEN 0 WHEN 'warning' THEN 1 ELSE 2 END"
    filters  = []
    params   = []

    if alert_id:
        filters.append("a.id = ?")
        params.append(alert_id)
    if session_id:
        filters.append("a.session_id = ?")
        params.append(session_id)
    if unacknowledged_only:
        filters.append("a.acknowledged = 0")

    where = ("WHERE " + " AND ".join(filters)) if filters else ""

    rows = conn.execute(
        f"SELECT a.*, s.name AS session_name, s.game_name "
        f"FROM alerts a JOIN sessions s ON s.id = a.session_id "
        f"{where} ORDER BY {severity_order}, a.created_at DESC",
        params
    ).fetchall()

    conn.close()
    return [
        {
            "id":           r["id"],
            "session_id":   r["session_id"],
            "session_name": r["session_name"],
            "game_name":    r["game_name"],
            "rule":         r["rule"],
            "message":      r["message"],
            "severity":     r["severity"],
            "acknowledged": bool(r["acknowledged"]),
            "created_at":   r["created_at"],
        }
        for r in rows
    ]


def acknowledge_alert(alert_id: int) -> bool:
    """Mark an alert as acknowledged. Returns True if found and updated."""
    conn = get_connection()
    cur = conn.execute(
        "UPDATE alerts SET acknowledged = 1 WHERE id = ?", (alert_id,))
    conn.commit()
    conn.close()
    return cur.rowcount > 0


def generate_and_persist_alerts(session_id: int) -> list:
    """
    Re-run alert rules against a session and persist results.
    Clears existing alerts for session first.
    """
    conn = get_connection()
    s = conn.execute("SELECT * FROM sessions WHERE id = ?", (session_id,)).fetchone()
    if not s:
        conn.close()
        return []

    conn.execute("DELETE FROM alerts WHERE session_id = ?", (session_id,))

    new_alerts = []

    if s["rtp"] < THRESHOLDS["rtp_critical"]:
        new_alerts.append(dict(
            session_id=session_id, rule="rtp_critical",
            message=f"RTP {s['rtp']}% is below the critical threshold of "
                    f"{THRESHOLDS['rtp_critical']}%.",
            severity="critical", acknowledged=0))

    elif s["rtp"] < THRESHOLDS["rtp_warning"]:
        new_alerts.append(dict(
            session_id=session_id, rule="rtp_warning",
            message=f"RTP {s['rtp']}% is below the warning threshold of "
                    f"{THRESHOLDS['rtp_warning']}%.",
            severity="warning", acknowledged=0))

    if s["net_result"] < -THRESHOLDS["max_loss"]:
        new_alerts.append(dict(
            session_id=session_id, rule="large_loss",
            message=f"Net loss of ${abs(s['net_result']):.2f} exceeds the "
                    f"${THRESHOLDS['max_loss']:.0f} loss threshold.",
            severity="warning", acknowledged=0))

    if s["losing_streak"] > THRESHOLDS["streak_critical"]:
        new_alerts.append(dict(
            session_id=session_id, rule="streak_critical",
            message=f"Losing streak of {s['losing_streak']} spins exceeds the critical "
                    f"threshold of {THRESHOLDS['streak_critical']}.",
            severity="critical", acknowledged=0))

    elif s["losing_streak"] > THRESHOLDS["streak_warning"]:
        new_alerts.append(dict(
            session_id=session_id, rule="streak_warning",
            message=f"Losing streak of {s['losing_streak']} spins flagged for review.",
            severity="warning", acknowledged=0))

    for al in new_alerts:
        conn.execute(
            "INSERT INTO alerts (session_id, rule, message, severity, acknowledged) "
            "VALUES (:session_id, :rule, :message, :severity, :acknowledged)", al)

    conn.commit()
    conn.close()
    return new_alerts


def get_alert_summary() -> dict:
    """Return counts by severity for dashboard badge display."""
    conn = get_connection()
    row = conn.execute("""
        SELECT
            COUNT(*) AS total,
            COUNT(CASE WHEN severity='critical' AND acknowledged=0 THEN 1 END) AS critical,
            COUNT(CASE WHEN severity='warning'  AND acknowledged=0 THEN 1 END) AS warning,
            COUNT(CASE WHEN acknowledged=0 THEN 1 END) AS unacknowledged
        FROM alerts
    """).fetchone()
    conn.close()
    return {
        "total":          row["total"],
        "critical":       row["critical"],
        "warning":        row["warning"],
        "unacknowledged": row["unacknowledged"],
    }


def check_rtp_decay_drift(session_id: int, window_spins: int = 30) -> dict:
    """
    Detect real-time RTP decay/drift during a session.
    Triggers an alert if rolling RTP drops severely over consecutive spins.
    """
    conn = get_connection()
    events = conn.execute(
        "SELECT bet_amount, win_amount FROM events WHERE session_id=? ORDER BY timestamp",
        (session_id,)
    ).fetchall()
    conn.close()

    if len(events) < window_spins:
        return {"decay_detected": False, "rolling_rtp": None}

    recent_events = events[-window_spins:]
    total_bets = sum(e["bet_amount"] or 0 for e in recent_events)
    total_wins = sum(e["win_amount"] or 0 for e in recent_events)

    if total_bets == 0:
        return {"decay_detected": False, "rolling_rtp": 0.0}

    rolling_rtp = round((total_wins / total_bets) * 100.0, 2)
    decay_detected = rolling_rtp < 70.0

    return {
        "session_id": session_id,
        "decay_detected": decay_detected,
        "rolling_rtp": rolling_rtp,
        "window_spins": window_spins,
        "severity": "critical" if rolling_rtp < 50.0 else ("warning" if decay_detected else "none")
    }

"""
engines/analysis_engine.py
---------------------------
Computes real aggregate metrics from session and event data.
Routes call this — no raw SQL in routes.

Maturity: Working Prototype
Future:   Add time-series aggregation, percentile scoring, peer benchmarking.
"""

from database.db import get_connection


def get_global_metrics() -> dict:
    """
    Return platform-wide KPI summary across all sessions.
    Used by the dashboard KPI strip.
    """
    conn = get_connection()

    row = conn.execute("""
        SELECT
            COUNT(*)                        AS total_sessions,
            ROUND(SUM(net_result), 2)       AS total_net,
            ROUND(AVG(rtp), 2)              AS avg_rtp,
            ROUND(AVG(net_result), 2)       AS avg_net,
            ROUND(SUM(total_bets), 2)       AS total_wagered,
            ROUND(SUM(total_wins), 2)       AS total_returned,
            ROUND(AVG(duration_minutes), 0) AS avg_duration,
            SUM(spins)                      AS total_spins,
            ROUND(MAX(biggest_win), 2)      AS all_time_biggest_win,
            ROUND(MAX(losing_streak), 0)    AS worst_streak,
            COUNT(CASE WHEN status='flagged' THEN 1 END) AS flagged_count
        FROM sessions
    """).fetchone()

    conn.close()

    return {
        "total_sessions":      row["total_sessions"]      or 0,
        "total_net":           row["total_net"]           or 0.0,
        "avg_rtp":             row["avg_rtp"]             or 0.0,
        "avg_net":             row["avg_net"]             or 0.0,
        "total_wagered":       row["total_wagered"]       or 0.0,
        "total_returned":      row["total_returned"]      or 0.0,
        "avg_duration":        row["avg_duration"]        or 0,
        "total_spins":         row["total_spins"]         or 0,
        "all_time_biggest_win": row["all_time_biggest_win"] or 0.0,
        "worst_streak":        row["worst_streak"]        or 0,
        "flagged_count":       row["flagged_count"]       or 0,
    }


def get_session_metrics(session_id: int) -> dict | None:
    """Return detailed metrics for a single session."""
    conn = get_connection()

    s = conn.execute(
        "SELECT * FROM sessions WHERE id = ?", (session_id,)
    ).fetchone()

    if not s:
        conn.close()
        return None

    # Drawdown: largest balance drop within session events
    events = conn.execute(
        "SELECT balance_after FROM events WHERE session_id = ? ORDER BY timestamp",
        (session_id,)
    ).fetchall()
    conn.close()

    balances    = [e["balance_after"] for e in events]
    peak        = s["start_balance"]
    max_drawdown = 0.0
    for b in balances:
        if b > peak:
            peak = b
        dd = peak - b
        if dd > max_drawdown:
            max_drawdown = dd

    return {
        "id":               s["id"],
        "name":             s["name"],
        "game_name":        s["game_name"],
        "platform":         s["platform"],
        "date":             s["date"],
        "duration_minutes": s["duration_minutes"],
        "start_balance":    s["start_balance"],
        "end_balance":      s["end_balance"],
        "net_result":       s["net_result"],
        "total_bets":       s["total_bets"],
        "total_wins":       s["total_wins"],
        "rtp":              s["rtp"],
        "spins":            s["spins"],
        "biggest_win":      s["biggest_win"],
        "biggest_loss":     s["biggest_loss"],
        "losing_streak":    s["losing_streak"],
        "max_drawdown":     round(max_drawdown, 2),
        "status":           s["status"],
        "notes":            s["notes"],
    }


def get_rtp_distribution() -> list:
    """
    Return session count bucketed by RTP range.
    Used for histogram charts on the dashboard.
    """
    conn = get_connection()
    rows = conn.execute("""
        SELECT
            CASE
                WHEN rtp < 80  THEN 'Under 80%'
                WHEN rtp < 90  THEN '80–90%'
                WHEN rtp < 96  THEN '90–96%'
                WHEN rtp < 100 THEN '96–100%'
                ELSE 'Over 100%'
            END AS bucket,
            COUNT(*) AS count
        FROM sessions
        GROUP BY bucket
        ORDER BY MIN(rtp)
    """).fetchall()
    conn.close()
    return [{"bucket": r["bucket"], "count": r["count"]} for r in rows]


def get_net_result_over_time() -> list:
    """
    Return cumulative net result by date for line charts.
    """
    conn = get_connection()
    rows = conn.execute("""
        SELECT date, ROUND(SUM(net_result), 2) AS daily_net
        FROM sessions
        GROUP BY date
        ORDER BY date
    """).fetchall()
    conn.close()

    cumulative = 0.0
    result = []
    for r in rows:
        cumulative = round(cumulative + r["daily_net"], 2)
        result.append({"date": r["date"], "daily_net": r["daily_net"],
                       "cumulative_net": cumulative})
    return result


def get_performance_by_game() -> list:
    """Return avg RTP and net per game for the compare/breakdown view."""
    conn = get_connection()
    rows = conn.execute("""
        SELECT
            game_name,
            COUNT(*)                  AS sessions,
            ROUND(AVG(rtp), 2)        AS avg_rtp,
            ROUND(SUM(net_result), 2) AS total_net,
            ROUND(AVG(net_result), 2) AS avg_net
        FROM sessions
        GROUP BY game_name
        ORDER BY avg_rtp DESC
    """).fetchall()
    conn.close()
    return [dict(r) for r in rows]

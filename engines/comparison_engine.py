"""
engines/comparison_engine.py
-----------------------------
Compare two or more sessions and produce a structured diff summary.

Maturity: Working Prototype — structural comparison works.
Future:   Similarity scoring, visual overlay data, narrative AI summary (V10+).
"""

from database.db import get_connection


def compare_sessions(session_ids: list[int]) -> dict:
    """
    Compare a list of sessions by key metrics.
    Returns per-session metrics + a diff summary for the two most extreme values.
    """
    if not session_ids or len(session_ids) < 2:
        return {"error": "Provide at least two session IDs to compare."}

    conn = get_connection()
    placeholders = ",".join("?" * len(session_ids))
    rows = conn.execute(
        f"SELECT * FROM sessions WHERE id IN ({placeholders})", session_ids
    ).fetchall()
    conn.close()

    if not rows:
        return {"error": "No sessions found for the provided IDs."}

    sessions = [dict(r) for r in rows]

    # ── Per-session summary ────────────────────────────────────────────────────
    summaries = []
    for s in sessions:
        summaries.append({
            "id":               s["id"],
            "name":             s["name"],
            "game_name":        s["game_name"],
            "platform":         s["platform"],
            "date":             s["date"],
            "duration_minutes": s["duration_minutes"],
            "net_result":       s["net_result"],
            "rtp":              s["rtp"],
            "spins":            s["spins"],
            "total_bets":       s["total_bets"],
            "biggest_win":      s["biggest_win"],
            "losing_streak":    s["losing_streak"],
            "status":           s["status"],
        })

    # ── Diff summary across sessions ──────────────────────────────────────────
    rtps    = [s["rtp"]        for s in sessions]
    nets    = [s["net_result"] for s in sessions]
    streaks = [s["losing_streak"] for s in sessions]

    diff = {
        "rtp_range":     {"min": min(rtps),    "max": max(rtps),    "delta": round(max(rtps) - min(rtps), 2)},
        "net_range":     {"min": min(nets),    "max": max(nets),    "delta": round(max(nets) - min(nets), 2)},
        "streak_range":  {"min": min(streaks), "max": max(streaks), "delta": max(streaks) - min(streaks)},
        "best_rtp_session":  sessions[rtps.index(max(rtps))]["name"],
        "worst_rtp_session": sessions[rtps.index(min(rtps))]["name"],
        "best_net_session":  sessions[nets.index(max(nets))]["name"],
        "worst_net_session": sessions[nets.index(min(nets))]["name"],
    }

    # ── Narrative summary (rule-based; AI-enhanced in V13) ────────────────────
    narrative = _build_narrative(sessions, diff)

    return {
        "sessions":  summaries,
        "diff":      diff,
        "narrative": narrative,
    }


def _build_narrative(sessions: list, diff: dict) -> str:
    """Simple rule-based comparison narrative."""
    lines = []

    if diff["rtp_range"]["delta"] > 10:
        lines.append(
            f"Large RTP variance of {diff['rtp_range']['delta']:.1f}% across sessions. "
            f"'{diff['best_rtp_session']}' performed best at {diff['rtp_range']['max']:.1f}%, "
            f"while '{diff['worst_rtp_session']}' returned only {diff['rtp_range']['min']:.1f}%."
        )
    else:
        lines.append(
            f"Sessions showed consistent RTP performance "
            f"(range: {diff['rtp_range']['min']:.1f}% – {diff['rtp_range']['max']:.1f}%)."
        )

    if diff["net_range"]["delta"] > 100:
        lines.append(
            f"Net result spread of ${diff['net_range']['delta']:.2f}. "
            f"Best session: '{diff['best_net_session']}' "
            f"(${diff['net_range']['max']:.2f}). "
            f"Worst session: '{diff['worst_net_session']}' "
            f"(${diff['net_range']['min']:.2f})."
        )

    if diff["streak_range"]["max"] > 10:
        lines.append(
            f"Highest recorded losing streak was {diff['streak_range']['max']} spins. "
            f"High-streak sessions warrant risk review."
        )

    return " ".join(lines) if lines else "Sessions are broadly comparable across key metrics."

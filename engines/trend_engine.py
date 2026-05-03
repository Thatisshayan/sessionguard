"""
engines/trend_engine.py
------------------------
Phase 9 + 10: Session trend analysis, health scoring, and pattern memory.

Covers:
  - Rolling RTP + net trend over last N sessions
  - Session streak detector (winning/losing runs)
  - Session health score (composite 0-100)
  - Drift projector (trajectory extrapolation)
  - Early warning heuristics
  - Pattern memory (behavior change tracking over time)
  - Volatility forecast

Product direction: behaviour analysis, NOT outcome prediction.
These engines answer "how is this player trending" not "what will happen next".

Maturity: Working Prototype
Future:   ML-based cluster comparison (V12), full anomaly detection (V13).
"""

from __future__ import annotations
import math
from datetime import datetime
from database.db import get_connection


# ── Helpers ───────────────────────────────────────────────────────────────────

def _safe(v, default=0.0) -> float:
    try:
        return float(v) if v is not None else default
    except Exception:
        return default


def _linear_trend(values: list[float]) -> dict:
    """Compute slope, direction, and R² for a series."""
    n = len(values)
    if n < 2:
        return {"slope": 0.0, "direction": "flat", "r2": 0.0, "pct_change": 0.0}

    x_mean = (n - 1) / 2
    y_mean = sum(values) / n

    ss_xy = sum((i - x_mean) * (values[i] - y_mean) for i in range(n))
    ss_xx = sum((i - x_mean) ** 2 for i in range(n)) or 1e-9
    ss_yy = sum((values[i] - y_mean) ** 2 for i in range(n)) or 1e-9

    slope = ss_xy / ss_xx
    r2    = (ss_xy ** 2) / (ss_xx * ss_yy)

    pct_change = ((values[-1] - values[0]) / (abs(values[0]) + 1e-9)) * 100

    direction = "flat"
    if slope > 0.5:   direction = "improving"
    elif slope < -0.5: direction = "declining"

    return {
        "slope":      round(slope, 4),
        "direction":  direction,
        "r2":         round(r2, 4),
        "pct_change": round(pct_change, 1),
    }


# ── Rolling trend engine ──────────────────────────────────────────────────────

def get_rolling_trends(last_n: int = 10) -> dict:
    """
    Compute rolling trends across the last N sessions.
    Returns per-metric trend with slope, direction, and % change.
    """
    conn = get_connection()
    rows = conn.execute(
        "SELECT id, name, date, rtp, net_result, spins, losing_streak, total_bets "
        "FROM sessions ORDER BY date DESC, id DESC LIMIT ?",
        (last_n,)
    ).fetchall()
    conn.close()

    if len(rows) < 2:
        return {"status": "insufficient_data", "sessions_analysed": len(rows)}

    # Reverse so oldest first
    sessions = [dict(r) for r in reversed(rows)]

    rtp_vals     = [_safe(s["rtp"])           for s in sessions]
    net_vals     = [_safe(s["net_result"])     for s in sessions]
    spins_vals   = [_safe(s["spins"])          for s in sessions]
    streak_vals  = [_safe(s["losing_streak"])  for s in sessions]

    rtp_trend    = _linear_trend(rtp_vals)
    net_trend    = _linear_trend(net_vals)
    spins_trend  = _linear_trend(spins_vals)
    streak_trend = _linear_trend(streak_vals)

    # Overall trend verdict
    improving = sum(1 for t in [rtp_trend, net_trend]    if t["direction"] == "improving")
    declining = sum(1 for t in [rtp_trend, net_trend]    if t["direction"] == "declining")
    verdict   = "improving" if improving > declining else "declining" if declining > improving else "mixed"

    return {
        "status":            "ok",
        "sessions_analysed": len(sessions),
        "window":            last_n,
        "overall_verdict":   verdict,
        "trends": {
            "rtp":           {**rtp_trend,    "values": [round(v, 2) for v in rtp_vals]},
            "net_result":    {**net_trend,    "values": [round(v, 2) for v in net_vals]},
            "spins":         {**spins_trend,  "values": [int(v) for v in spins_vals]},
            "losing_streak": {**streak_trend, "values": [int(v) for v in streak_vals]},
        },
        "session_dates":     [s["date"] for s in sessions],
        "session_names":     [s["name"] for s in sessions],
    }


# ── Session streak detector ───────────────────────────────────────────────────

def get_session_streaks() -> dict:
    """
    Detect winning/losing session streaks.
    A 'winning session' = net_result > 0.
    Returns current streak, longest streak, and streak history.
    """
    conn = get_connection()
    rows = conn.execute(
        "SELECT id, name, date, net_result FROM sessions ORDER BY date ASC, id ASC"
    ).fetchall()
    conn.close()

    if not rows:
        return {"current_streak": 0, "current_type": None, "streaks": []}

    sessions     = [dict(r) for r in rows]
    streaks      = []
    cur_type     = "win" if sessions[0]["net_result"] >= 0 else "loss"
    cur_count    = 1
    cur_start    = sessions[0]["date"]

    for s in sessions[1:]:
        s_type = "win" if s["net_result"] >= 0 else "loss"
        if s_type == cur_type:
            cur_count += 1
        else:
            streaks.append({"type": cur_type, "length": cur_count, "start": cur_start})
            cur_type  = s_type
            cur_count = 1
            cur_start = s["date"]
    streaks.append({"type": cur_type, "length": cur_count, "start": cur_start})

    # Current streak
    current = streaks[-1]
    longest_win  = max((s["length"] for s in streaks if s["type"] == "win"),  default=0)
    longest_loss = max((s["length"] for s in streaks if s["type"] == "loss"), default=0)

    return {
        "current_streak":  current["length"],
        "current_type":    current["type"],
        "longest_win":     longest_win,
        "longest_loss":    longest_loss,
        "total_sessions":  len(sessions),
        "winning_sessions": sum(1 for s in sessions if s["net_result"] >= 0),
        "losing_sessions":  sum(1 for s in sessions if s["net_result"] < 0),
        "streak_history":  streaks[-10:],   # last 10 streaks
    }


# ── Session health score (0-100) ──────────────────────────────────────────────

def get_session_health(session_id: int) -> dict:
    """
    Composite health score for a session (0=worst, 100=best).

    Components:
      - RTP score     (30 pts) — how close to or above break-even
      - Streak score  (25 pts) — losing streak relative to spins
      - Confidence    (20 pts) — avg OCR/event confidence
      - Trend score   (25 pts) — whether session drifted up or down
    """
    conn = get_connection()
    s    = conn.execute("SELECT * FROM sessions WHERE id=?", (session_id,)).fetchone()
    if not s:
        conn.close()
        return {"error": f"Session {session_id} not found."}

    events = conn.execute(
        "SELECT balance_after, confidence_score FROM events "
        "WHERE session_id=? ORDER BY timestamp",
        (session_id,)
    ).fetchall()
    conn.close()

    rtp        = _safe(s["rtp"])
    streak     = _safe(s["losing_streak"])
    spins      = max(_safe(s["spins"]), 1)
    net        = _safe(s["net_result"])
    start_bal  = max(_safe(s["start_balance"]), 1)

    # RTP score — 96%+ = 30pts, 85%+ = 15pts, below = scaled
    rtp_score  = 30 if rtp >= 96 else 15 if rtp >= 85 else max(0, round(rtp / 96 * 30, 1))

    # Streak score — 0 streak = 25pts, proportional decline
    streak_ratio = min(streak / spins, 1.0)
    streak_score = round((1 - streak_ratio) * 25, 1)

    # Confidence score
    if events:
        confs    = [_safe(e["confidence_score"], 0.8) for e in events]
        avg_conf = sum(confs) / len(confs)
        conf_score = round(avg_conf * 20, 1)
    else:
        conf_score = 15.0  # default if no event data

    # Trend score — balance curve slope direction
    if len(events) >= 3:
        bals  = [_safe(e["balance_after"]) for e in events]
        trend = _linear_trend(bals)
        if trend["direction"] == "improving":
            trend_score = 25.0
        elif trend["direction"] == "flat":
            trend_score = 12.5
        else:
            trend_score = max(0, 25 - abs(trend["slope"]) * 10)
    else:
        trend_score = 12.5

    total = round(rtp_score + streak_score + conf_score + trend_score, 1)
    total = min(100.0, max(0.0, total))

    level = "excellent" if total >= 80 else "good" if total >= 60 else "fair" if total >= 40 else "poor"

    return {
        "session_id":    session_id,
        "health_score":  total,
        "health_level":  level,
        "components": {
            "rtp_score":    rtp_score,
            "streak_score": streak_score,
            "conf_score":   conf_score,
            "trend_score":  trend_score,
        },
        "inputs": {
            "rtp":          rtp,
            "losing_streak": streak,
            "spins":        int(spins),
            "net_result":   net,
            "event_count":  len(events),
        },
    }


# ── Drift projector (Phase 10 analytics) ─────────────────────────────────────

def project_session_drift(session_id: int, project_n: int = 20) -> dict:
    """
    Extrapolate the current session's balance trajectory.
    Projects the next `project_n` spins based on the current slope.

    This is BEHAVIOUR ANALYSIS — it shows where the trajectory is heading
    based on observed data. It does NOT predict RNG outcomes.
    """
    conn = get_connection()
    events = conn.execute(
        "SELECT balance_after FROM events WHERE session_id=? ORDER BY timestamp",
        (session_id,)
    ).fetchall()
    conn.close()

    bals = [_safe(e["balance_after"]) for e in events]
    if len(bals) < 5:
        return {"status": "insufficient_data", "need": 5, "have": len(bals)}

    trend = _linear_trend(bals)
    slope = trend["slope"]
    last  = bals[-1]

    # Linear extrapolation — not a prediction, a trajectory extension
    projected = [round(last + slope * i, 2) for i in range(1, project_n + 1)]
    crossover = None  # Spin where projected hits zero/bust
    for i, val in enumerate(projected):
        if val <= 0:
            crossover = i + 1
            break

    confidence = min(trend["r2"] * 100, 85)  # cap at 85% — never claim certainty

    return {
        "status":          "ok",
        "session_id":      session_id,
        "observed_spins":  len(bals),
        "current_balance": last,
        "slope_per_spin":  round(slope, 4),
        "direction":       trend["direction"],
        "projected_next":  projected,
        "projected_spins": list(range(len(bals)+1, len(bals)+project_n+1)),
        "bust_spin":       crossover,  # None if trajectory stays positive
        "trajectory_confidence": round(confidence, 1),
        "disclaimer":      "Projection based on observed trend only. RNG outcomes are independent of history.",
    }


# ── Early warning heuristics ──────────────────────────────────────────────────

def get_early_warnings(session_id: int) -> list[dict]:
    """
    Real-time early warnings for a session based on observable patterns.
    Fires before formal alerts — designed to catch problems early.
    """
    conn = get_connection()
    s    = conn.execute("SELECT * FROM sessions WHERE id=?", (session_id,)).fetchone()
    if not s:
        conn.close()
        return []

    events = conn.execute(
        "SELECT bet_amount, win_amount, balance_after FROM events "
        "WHERE session_id=? ORDER BY timestamp",
        (session_id,)
    ).fetchall()
    conn.close()

    warnings = []
    spins    = max(_safe(s["spins"]), 1)
    rtp      = _safe(s["rtp"])
    streak   = _safe(s["losing_streak"])
    bals     = [_safe(e["balance_after"]) for e in events]
    bets     = [_safe(e["bet_amount"])    for e in events]

    # W1: RTP sliding below 90% in last 20 spins
    if len(bals) >= 20:
        recent_bets = [_safe(e["bet_amount"]) for e in events[-20:]]
        recent_wins = [_safe(e["win_amount"])  for e in events[-20:]]
        recent_rtp  = (sum(recent_wins) / max(sum(recent_bets), 1)) * 100
        if recent_rtp < 90 and rtp > recent_rtp + 5:
            warnings.append({
                "code":     "W1_RECENT_RTP_DROP",
                "severity": "warning",
                "message":  f"RTP dropped to {recent_rtp:.0f}% in last 20 spins (overall {rtp:.0f}%).",
                "detail":   "Recent session performance significantly worse than overall average.",
            })

    # W2: Balance declining despite positive overall RTP
    if len(bals) >= 10:
        trend = _linear_trend(bals[-10:])
        if trend["direction"] == "declining" and rtp >= 95:
            warnings.append({
                "code":     "W2_BALANCE_DRIFT",
                "severity": "info",
                "message":  "Balance trending down despite reasonable RTP.",
                "detail":   "Bet sizing relative to balance may be creating drawdown pressure.",
            })

    # W3: Bet escalation detected
    if len(bets) >= 10:
        avg_early = sum(bets[:5]) / 5
        avg_late  = sum(bets[-5:]) / 5
        if avg_late > avg_early * 1.8:
            warnings.append({
                "code":     "W3_BET_ESCALATION",
                "severity": "warning",
                "message":  f"Bet size increased {avg_late/avg_early:.1f}x vs session start.",
                "detail":   "Possible tilt behaviour — bets growing faster than expected.",
            })

    # W4: Approaching long losing streak
    if streak >= 10 and streak < 15:
        warnings.append({
            "code":     "W4_LONG_STREAK_FORMING",
            "severity": "warning",
            "message":  f"Losing streak at {int(streak)} spins — approaching critical threshold.",
            "detail":   "Alert fires at 15. Consider reviewing session pace.",
        })

    # W5: Low balance relative to start
    if bals:
        start_bal = _safe(s["start_balance"], 1)
        pct_remaining = (bals[-1] / start_bal) * 100
        if pct_remaining < 30:
            warnings.append({
                "code":     "W5_LOW_BALANCE",
                "severity": "critical",
                "message":  f"Balance at {pct_remaining:.0f}% of starting amount.",
                "detail":   f"Current: ${bals[-1]:.2f} vs start: ${start_bal:.2f}",
            })

    return warnings


# ── Pattern memory (cross-session behavior change tracking) ───────────────────

def get_pattern_memory(last_n: int = 20) -> dict:
    """
    Track how the player's behavior patterns have changed over their last N sessions.
    Compares early sessions vs recent sessions across key behavioral metrics.
    """
    conn = get_connection()
    rows = conn.execute(
        "SELECT id, date, rtp, net_result, losing_streak, total_bets, spins "
        "FROM sessions ORDER BY date ASC, id ASC LIMIT ?",
        (last_n,)
    ).fetchall()
    conn.close()

    sessions = [dict(r) for r in rows]
    if len(sessions) < 6:
        return {"status": "insufficient_data", "sessions": len(sessions)}

    mid  = len(sessions) // 2
    early  = sessions[:mid]
    recent = sessions[mid:]

    def _avg(lst, key, default=0.0):
        vals = [_safe(s[key]) for s in lst]
        return round(sum(vals) / len(vals), 2) if vals else default

    def _change(old, new):
        if old == 0: return 0.0
        return round((new - old) / abs(old) * 100, 1)

    metrics = {}
    for key in ["rtp", "net_result", "losing_streak"]:
        e_avg = _avg(early,  key)
        r_avg = _avg(recent, key)
        chg   = _change(e_avg, r_avg)
        metrics[key] = {
            "early_avg":  e_avg,
            "recent_avg": r_avg,
            "change_pct": chg,
            "direction":  "improving" if (
                (key in ["rtp","net_result"] and chg > 2) or
                (key == "losing_streak" and chg < -5)
            ) else "declining" if (
                (key in ["rtp","net_result"] and chg < -2) or
                (key == "losing_streak" and chg > 5)
            ) else "stable",
        }

    improving = sum(1 for m in metrics.values() if m["direction"] == "improving")
    declining = sum(1 for m in metrics.values() if m["direction"] == "declining")
    overall   = "improving" if improving > declining else "declining" if declining > improving else "stable"

    return {
        "status":           "ok",
        "sessions_total":   len(sessions),
        "early_window":     f"{early[0]['date']} → {early[-1]['date']}",
        "recent_window":    f"{recent[0]['date']} → {recent[-1]['date']}",
        "overall_direction": overall,
        "metrics":          metrics,
        "summary": (
            f"Behaviour is {overall}. "
            f"RTP {metrics['rtp']['direction']} "
            f"({metrics['rtp']['early_avg']}% → {metrics['rtp']['recent_avg']}%). "
            f"Net result {metrics['net_result']['direction']}."
        ),
    }

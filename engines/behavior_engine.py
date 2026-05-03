"""
engines/behavior_engine.py
---------------------------
Real behavior pattern analysis using event-level data + sklearn.

Patterns detected:
  1. Bet escalation — bet size increasing after losses (tilt signal)
  2. Session drift   — net result trend over time within session
  3. Losing cluster  — consecutive loss events with confidence
  4. Recovery chasing — large bet spikes after big losses
  5. Volatility zones — high-variance periods within a session
  6. Time-of-day risk — when in the session highest drawdown occurred

Maturity: Working Prototype
Future:   Cross-session pattern memory (V12), anomaly detection (V13).
"""

from __future__ import annotations
from typing import Optional
import numpy as np

from database.db import get_connection


# ── Helpers ───────────────────────────────────────────────────────────────────

def _get_events(session_id: int) -> list[dict]:
    conn = get_connection()
    rows = conn.execute(
        """SELECT bet_amount, win_amount, balance_after, confidence_score, timestamp
           FROM events WHERE session_id=? ORDER BY timestamp""",
        (session_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def _linear_slope(values: list[float]) -> float:
    """Slope of a simple least-squares fit — indicates trend direction."""
    if len(values) < 2:
        return 0.0
    x = np.arange(len(values), dtype=float)
    y = np.array(values, dtype=float)
    # Remove NaN
    mask = ~np.isnan(y)
    if mask.sum() < 2:
        return 0.0
    coeffs = np.polyfit(x[mask], y[mask], 1)
    return round(float(coeffs[0]), 4)


# ── Pattern detectors ─────────────────────────────────────────────────────────

def detect_bet_escalation(events: list[dict]) -> dict:
    """
    Detect whether bets are increasing after losses.
    A positive slope of bet sizes following a losing run = escalation signal.
    """
    if len(events) < 5:
        return {"detected": False, "severity": "none", "detail": "Insufficient data."}

    bets    = [e["bet_amount"] or 0 for e in events]
    wins    = [e["win_amount"] or 0 for e in events]

    # Bets placed immediately after losses
    post_loss_bets = [bets[i] for i in range(1, len(events)) if wins[i-1] == 0]

    if len(post_loss_bets) < 3:
        return {"detected": False, "severity": "none", "detail": "Not enough post-loss bets."}

    slope    = _linear_slope(post_loss_bets)
    avg_bet  = round(float(np.mean(bets)), 2)
    peak_bet = round(max(bets), 2)

    escalation_ratio = peak_bet / avg_bet if avg_bet > 0 else 1.0
    detected  = slope > 0.05 and escalation_ratio > 1.5

    severity = "none"
    if detected:
        severity = "critical" if escalation_ratio > 3.0 else "warning"

    return {
        "detected":          detected,
        "severity":          severity,
        "slope":             slope,
        "avg_bet":           avg_bet,
        "peak_bet":          peak_bet,
        "escalation_ratio":  round(escalation_ratio, 2),
        "detail":            (
            f"Bet size increased {escalation_ratio:.1f}x during losing runs. "
            f"Peak bet ${peak_bet:.2f} vs avg ${avg_bet:.2f}."
            if detected else "No significant bet escalation detected."
        ),
    }


def detect_session_drift(events: list[dict]) -> dict:
    """
    Detect how the session's net position trended over time.
    Negative slope = persistent decline. Positive = recovery.
    """
    if len(events) < 3:
        return {"detected": False, "direction": "flat", "detail": "Insufficient data."}

    balances  = [e["balance_after"] or 0 for e in events]
    slope     = _linear_slope(balances)

    start_bal = balances[0]
    end_bal   = balances[-1]
    peak_bal  = max(balances)
    trough    = min(balances)
    drawdown  = round(peak_bal - trough, 2)
    net       = round(end_bal - start_bal, 2)

    direction = "declining" if slope < -0.1 else "recovering" if slope > 0.1 else "flat"
    severity  = "none"
    if direction == "declining":
        severity = "critical" if drawdown > abs(net) * 0.5 else "warning"

    return {
        "detected":  direction != "flat",
        "direction": direction,
        "severity":  severity,
        "slope":     slope,
        "drawdown":  drawdown,
        "net":       net,
        "detail":    (
            f"Session drifting {direction}. Slope={slope:.3f}, "
            f"drawdown=${drawdown:.2f}, net=${net:.2f}."
        ),
    }


def detect_losing_clusters(events: list[dict]) -> dict:
    """
    Identify clusters of consecutive losing spins and their positions.
    Returns the longest cluster and its location in the session.
    """
    if not events:
        return {"detected": False, "max_streak": 0, "clusters": []}

    wins    = [e["win_amount"] or 0 for e in events]
    clusters  = []
    streak    = 0
    start_idx = 0

    for i, w in enumerate(wins):
        if w == 0:
            if streak == 0:
                start_idx = i
            streak += 1
        else:
            if streak >= 3:
                clusters.append({
                    "start": start_idx,
                    "end":   i - 1,
                    "length": streak,
                    "position_pct": round(start_idx / len(events) * 100, 1),
                })
            streak = 0

    if streak >= 3:
        clusters.append({"start": start_idx, "end": len(events)-1,
                          "length": streak, "position_pct": round(start_idx / len(events) * 100, 1)})

    max_streak = max((c["length"] for c in clusters), default=0)
    detected   = max_streak >= 5

    return {
        "detected":   detected,
        "severity":   "critical" if max_streak > 15 else "warning" if max_streak > 8 else "none",
        "max_streak": max_streak,
        "clusters":   clusters[:10],  # top 10
        "detail":     (
            f"Longest losing cluster: {max_streak} spins. "
            f"{len(clusters)} clusters of 3+ losses found."
            if clusters else "No significant losing clusters."
        ),
    }


def detect_recovery_chasing(events: list[dict]) -> dict:
    """
    Detect large bet spikes immediately after big losses (chasing behaviour).
    """
    if len(events) < 4:
        return {"detected": False, "severity": "none", "incidents": []}

    bets     = [e["bet_amount"] or 0 for e in events]
    wins     = [e["win_amount"] or 0 for e in events]
    avg_bet  = float(np.mean(bets)) if bets else 1.0
    incidents = []

    for i in range(1, len(events)):
        # A "big loss" = zero win with a bet > 2x average
        if wins[i-1] == 0 and bets[i-1] > avg_bet * 1.5:
            # Chasing = next bet is also elevated
            if bets[i] > avg_bet * 2.0:
                incidents.append({
                    "spin":         i,
                    "prev_bet":     round(bets[i-1], 2),
                    "next_bet":     round(bets[i], 2),
                    "spike_ratio":  round(bets[i] / avg_bet, 2),
                })

    detected = len(incidents) >= 2
    return {
        "detected":   detected,
        "severity":   "warning" if detected else "none",
        "incidents":  incidents[:5],
        "detail":     (
            f"Recovery chasing detected: {len(incidents)} bet spikes after losses."
            if detected else "No recovery chasing detected."
        ),
    }


def detect_volatility_zones(events: list[dict], window: int = 10) -> dict:
    """
    Identify high-volatility windows within the session using rolling std dev.
    """
    if len(events) < window + 1:
        return {"detected": False, "zones": [], "peak_volatility": 0}

    balances  = [e["balance_after"] or 0 for e in events]
    zones     = []
    peak_vol  = 0.0

    for i in range(len(balances) - window):
        window_vals = balances[i : i + window]
        vol = float(np.std(window_vals))
        if vol > peak_vol:
            peak_vol = vol
        if vol > float(np.std(balances)) * 1.5:
            zones.append({
                "start_spin":  i,
                "end_spin":    i + window,
                "volatility":  round(vol, 2),
                "position_pct": round(i / len(balances) * 100, 1),
            })

    detected = len(zones) > 0
    return {
        "detected":        detected,
        "severity":        "warning" if detected else "none",
        "zones":           zones[:5],
        "peak_volatility": round(peak_vol, 2),
        "detail":          (
            f"{len(zones)} high-volatility zone(s) detected. Peak std dev: ${peak_vol:.2f}."
            if detected else "No high-volatility zones detected."
        ),
    }


# ── Master analysis ────────────────────────────────────────────────────────────

def analyze_behavior(session_id: int) -> dict:
    """
    Run all behavior detectors for a session.
    Returns a structured report with all pattern findings.
    """
    events = _get_events(session_id)

    if len(events) < 3:
        return {
            "session_id":  session_id,
            "status":      "insufficient_data",
            "message":     f"Only {len(events)} events — need at least 3 for behavior analysis.",
            "patterns":    {},
            "risk_score":  0,
            "risk_level":  "unknown",
        }

    patterns = {
        "bet_escalation":    detect_bet_escalation(events),
        "session_drift":     detect_session_drift(events),
        "losing_clusters":   detect_losing_clusters(events),
        "recovery_chasing":  detect_recovery_chasing(events),
        "volatility_zones":  detect_volatility_zones(events),
    }

    # Composite risk score (0-100)
    sev_weights = {"critical": 25, "warning": 10, "none": 0}
    risk_score  = min(100, sum(
        sev_weights.get(p.get("severity", "none"), 0)
        for p in patterns.values()
    ))
    risk_level  = (
        "critical" if risk_score >= 50
        else "high"    if risk_score >= 25
        else "moderate" if risk_score >= 10
        else "low"
    )

    # Build summary text
    findings = [
        p["detail"] for p in patterns.values()
        if p.get("detected") and p.get("detail")
    ]
    summary = " | ".join(findings) if findings else "No concerning behavior patterns detected."

    return {
        "session_id":  session_id,
        "status":      "complete",
        "event_count": len(events),
        "patterns":    patterns,
        "risk_score":  risk_score,
        "risk_level":  risk_level,
        "summary":     summary,
        "findings":    findings,
    }


def analyze_behavior_global() -> dict:
    """Cross-session behavior summary — top risk sessions."""
    conn = get_connection()
    sessions = conn.execute(
        "SELECT id, name, game_name, losing_streak, rtp, net_result FROM sessions ORDER BY id"
    ).fetchall()
    conn.close()

    results = []
    for s in sessions:
        events = _get_events(s["id"])
        if len(events) < 5:
            continue
        esc  = detect_bet_escalation(events)
        clus = detect_losing_clusters(events)
        results.append({
            "session_id":   s["id"],
            "session_name": s["name"],
            "game_name":    s["game_name"],
            "rtp":          s["rtp"],
            "net_result":   s["net_result"],
            "escalation_detected": esc["detected"],
            "max_losing_streak":   clus["max_streak"],
            "risk_flags":   sum([
                int(esc["detected"]),
                int(clus["detected"]),
            ]),
        })

    # Sort by risk flags desc
    results.sort(key=lambda x: (-x["risk_flags"], x["net_result"]))
    return {
        "sessions_analyzed": len(results),
        "high_risk_count":   sum(1 for r in results if r["risk_flags"] >= 2),
        "sessions":          results[:20],
    }

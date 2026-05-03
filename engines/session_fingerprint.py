"""
engines/session_fingerprint.py
-------------------------------
Cross-session pattern memory using session fingerprints.
Each session gets a numeric feature vector. Cosine similarity
finds sessions with similar behavior patterns.

Features used:
  rtp, net_result_normalised, losing_streak, biggest_win_ratio,
  spins_bucket, duration_bucket, bet_escalation, session_drift_slope

Maturity: Working Prototype
Future:   sklearn KMeans clustering for automatic session grouping (V12).
          Anomaly detection for outlier sessions (V13).
"""

from __future__ import annotations
import json
import math
from typing import Optional

from database.db import get_connection


# ── Feature extraction ────────────────────────────────────────────────────────

def _safe(val, default=0.0) -> float:
    try:
        return float(val) if val is not None else default
    except Exception:
        return default


def extract_features(session_id: int) -> dict | None:
    """
    Extract a numeric feature vector for a session.
    Returns a dict of named features, or None if session not found.
    """
    conn = get_connection()
    s    = conn.execute("SELECT * FROM sessions WHERE id=?", (session_id,)).fetchone()
    if not s:
        conn.close()
        return None

    events = conn.execute(
        "SELECT bet_amount, win_amount, balance_after FROM events "
        "WHERE session_id=? ORDER BY timestamp", (session_id,)
    ).fetchall()
    conn.close()

    total_bets  = _safe(s["total_bets"],    1.0)
    spins       = max(_safe(s["spins"]),    1.0)
    start_bal   = max(_safe(s["start_balance"]), 1.0)

    # Drift slope from balance curve
    drift_slope = 0.0
    if len(events) >= 3:
        bals  = [float(e["balance_after"]) for e in events]
        n     = len(bals)
        x_mean = (n - 1) / 2
        y_mean = sum(bals) / n
        num   = sum((i - x_mean) * (bals[i] - y_mean) for i in range(n))
        den   = sum((i - x_mean) ** 2 for i in range(n)) or 1
        drift_slope = num / den

    features = {
        "rtp":                  _safe(s["rtp"]) / 100.0,          # 0-1+
        "net_ratio":            _safe(s["net_result"]) / start_bal, # -1 to +1
        "streak_ratio":         _safe(s["losing_streak"]) / spins,
        "win_ratio":            _safe(s["biggest_win"]) / total_bets,
        "spin_density":         min(spins / 500.0, 1.0),           # 0-1
        "duration_ratio":       min(_safe(s["duration_minutes"]) / 180.0, 1.0),
        "drift_slope_norm":     max(-1.0, min(1.0, drift_slope / (start_bal * 0.01 + 1e-9))),
        "bet_per_spin":         min(total_bets / (spins * 10.0), 1.0),
    }
    return features


def cosine_similarity(a: dict, b: dict) -> float:
    """Cosine similarity between two feature dicts."""
    keys = set(a) & set(b)
    if not keys:
        return 0.0
    dot   = sum(a[k] * b[k] for k in keys)
    mag_a = math.sqrt(sum(a[k] ** 2 for k in keys))
    mag_b = math.sqrt(sum(b[k] ** 2 for k in keys))
    if mag_a == 0 or mag_b == 0:
        return 0.0
    return round(dot / (mag_a * mag_b), 4)


# ── Session fingerprint store ─────────────────────────────────────────────────

def save_fingerprint(session_id: int) -> dict | None:
    """Extract and cache fingerprint in system_settings."""
    features = extract_features(session_id)
    if not features:
        return None
    conn = get_connection()
    conn.execute(
        "INSERT OR REPLACE INTO system_settings (key, value, updated_at) "
        "VALUES (?, ?, datetime('now'))",
        (f"fingerprint:{session_id}", json.dumps(features))
    )
    conn.commit()
    conn.close()
    return features


def get_fingerprint(session_id: int) -> dict | None:
    """Load cached fingerprint, or compute it fresh."""
    conn = get_connection()
    row  = conn.execute(
        "SELECT value FROM system_settings WHERE key=?",
        (f"fingerprint:{session_id}",)
    ).fetchone()
    conn.close()
    if row:
        try:
            return json.loads(row["value"])
        except Exception:
            pass
    return save_fingerprint(session_id)


# ── Similarity search ─────────────────────────────────────────────────────────

def find_similar_sessions(
    session_id: int,
    top_n:      int   = 5,
    min_score:  float = 0.85,
) -> list[dict]:
    """
    Find the top N most similar sessions to the given one.
    Returns list sorted by similarity score descending.
    """
    target = get_fingerprint(session_id)
    if not target:
        return []

    conn     = get_connection()
    sessions = conn.execute(
        "SELECT id, name, game_name, platform, rtp, net_result, date "
        "FROM sessions WHERE id != ?", (session_id,)
    ).fetchall()
    conn.close()

    results = []
    for s in sessions:
        fp = get_fingerprint(s["id"])
        if not fp:
            continue
        score = cosine_similarity(target, fp)
        if score >= min_score:
            results.append({
                "session_id":   s["id"],
                "session_name": s["name"],
                "game_name":    s["game_name"],
                "platform":     s["platform"],
                "rtp":          s["rtp"],
                "net_result":   s["net_result"],
                "date":         s["date"],
                "similarity":   score,
            })

    results.sort(key=lambda x: -x["similarity"])
    return results[:top_n]


def rebuild_all_fingerprints() -> int:
    """Recompute fingerprints for all sessions. Call after data changes."""
    conn = get_connection()
    ids  = [r[0] for r in conn.execute("SELECT id FROM sessions").fetchall()]
    conn.close()
    count = 0
    for sid in ids:
        if save_fingerprint(sid):
            count += 1
    return count

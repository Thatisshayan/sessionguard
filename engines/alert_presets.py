"""
engines/alert_presets.py
-------------------------
Saved alert threshold templates. Pre-built for common games/platforms.
Users can apply a preset to a session or profile instantly.

Maturity: Working Prototype
Future:   Community preset marketplace (V15).
"""

from __future__ import annotations
import json
from database.db import get_connection

# ── Built-in presets ──────────────────────────────────────────────────────────
BUILTIN_PRESETS = [
    {
        "name":        "Conservative",
        "description": "Tight limits for careful players",
        "game_family": "generic",
        "thresholds": {
            "rtp_warning":     98.0,
            "rtp_critical":    90.0,
            "max_loss":        100.0,
            "streak_warning":  5,
            "streak_critical": 10,
        },
    },
    {
        "name":        "Standard",
        "description": "Balanced thresholds for most sessions",
        "game_family": "generic",
        "thresholds": {
            "rtp_warning":     96.0,
            "rtp_critical":    85.0,
            "max_loss":        200.0,
            "streak_warning":  8,
            "streak_critical": 15,
        },
    },
    {
        "name":        "High Volatility",
        "description": "For high-variance games like Gates of Olympus or Sweet Bonanza",
        "game_family": "high_volatility",
        "thresholds": {
            "rtp_warning":     92.0,
            "rtp_critical":    78.0,
            "max_loss":        500.0,
            "streak_warning":  15,
            "streak_critical": 30,
        },
    },
    {
        "name":        "Low Volatility",
        "description": "For stable games like Starburst",
        "game_family": "low_volatility",
        "thresholds": {
            "rtp_warning":     97.0,
            "rtp_critical":    88.0,
            "max_loss":        75.0,
            "streak_warning":  4,
            "streak_critical": 8,
        },
    },
    {
        "name":        "Book Games",
        "description": "For Book of Dead, Book of Ra, and similar",
        "game_family": "book",
        "thresholds": {
            "rtp_warning":     94.0,
            "rtp_critical":    82.0,
            "max_loss":        300.0,
            "streak_warning":  12,
            "streak_critical": 20,
        },
    },
]


def seed_presets():
    """Insert built-in presets into system_settings if not already there."""
    conn = get_connection()
    for preset in BUILTIN_PRESETS:
        key = f"alert_preset:{preset['name']}"
        existing = conn.execute(
            "SELECT key FROM system_settings WHERE key=?", (key,)
        ).fetchone()
        if not existing:
            conn.execute(
                "INSERT INTO system_settings (key, value) VALUES (?,?)",
                (key, json.dumps(preset))
            )
    conn.commit()
    conn.close()


def get_all_presets() -> list[dict]:
    """Return all presets (built-in + user-created)."""
    conn    = get_connection()
    rows    = conn.execute(
        "SELECT key, value FROM system_settings WHERE key LIKE 'alert_preset:%' ORDER BY key"
    ).fetchall()
    conn.close()
    presets = []
    for row in rows:
        try:
            p = json.loads(row["value"])
            p["key"] = row["key"]
            presets.append(p)
        except Exception:
            pass
    return presets


def get_preset(name: str) -> dict | None:
    conn = get_connection()
    row  = conn.execute(
        "SELECT value FROM system_settings WHERE key=?",
        (f"alert_preset:{name}",)
    ).fetchone()
    conn.close()
    return json.loads(row["value"]) if row else None


def create_preset(name: str, description: str, game_family: str, thresholds: dict) -> dict:
    preset = {"name": name, "description": description,
              "game_family": game_family, "thresholds": thresholds}
    conn   = get_connection()
    conn.execute(
        "INSERT OR REPLACE INTO system_settings (key, value, updated_at) VALUES (?,?,datetime('now'))",
        (f"alert_preset:{name}", json.dumps(preset))
    )
    conn.commit()
    conn.close()
    return preset


def delete_preset(name: str) -> bool:
    # Cannot delete built-in presets
    builtin_names = {p["name"] for p in BUILTIN_PRESETS}
    if name in builtin_names:
        return False
    conn = get_connection()
    cur  = conn.execute("DELETE FROM system_settings WHERE key=?", (f"alert_preset:{name}",))
    conn.commit()
    conn.close()
    return cur.rowcount > 0


def apply_preset_to_profile(profile_id: int, preset_name: str) -> bool:
    """Apply a preset's thresholds to an existing profile's alert_rules."""
    preset = get_preset(preset_name)
    if not preset:
        return False
    conn = get_connection()
    conn.execute(
        "UPDATE profiles SET alert_rules=? WHERE id=?",
        (json.dumps(preset["thresholds"]), profile_id)
    )
    conn.commit()
    conn.close()
    return True

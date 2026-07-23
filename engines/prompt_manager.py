"""
engines/prompt_manager.py
-------------------------
Prompt versioning and A/B comparison framework.
Stores prompt templates in DB, supports versioning and activation.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Optional
from database.db import get_connection


@dataclass
class PromptVersion:
    id: int
    name: str
    version: int
    system_prompt: str
    model: str
    temperature: float
    max_tokens: int
    is_active: bool
    created_at: str


def create_prompt_version(
    name: str,
    system_prompt: str,
    version: Optional[int] = None,
    model: str = "nvidia/llama-3.1-nemotron-70b-instruct",
    temperature: float = 1.0,
    max_tokens: int = 1024,
    activate: bool = False,
) -> dict:
    """Create a new prompt version. Auto-increments version if not specified."""
    conn = get_connection()

    if version is None:
        row = conn.execute(
            "SELECT MAX(version) as max_v FROM prompt_versions WHERE name=?",
            (name,),
        ).fetchone()
        version = (row["max_v"] or 0) + 1 if row else 1

    cur = conn.execute(
        """INSERT INTO prompt_versions (name, version, system_prompt, model, temperature, max_tokens, is_active)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (name, version, system_prompt, model, temperature, max_tokens, 1 if activate else 0),
    )
    conn.commit()
    result = {"id": cur.lastrowid, "name": name, "version": version}
    conn.close()
    return result


def get_active_prompt(name: str = "session_analysis") -> Optional[dict]:
    """Get the currently active prompt version for a given name."""
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM prompt_versions WHERE name=? AND is_active=1 ORDER BY version DESC LIMIT 1",
        (name,),
    ).fetchone()
    conn.close()
    if row:
        return dict(row)
    return None


def list_versions(name: str = "session_analysis") -> list[dict]:
    """List all versions of a prompt."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM prompt_versions WHERE name=? ORDER BY version DESC",
        (name,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def activate_version(prompt_id: int) -> bool:
    """Activate a specific prompt version (deactivates others for same name)."""
    conn = get_connection()
    row = conn.execute("SELECT name FROM prompt_versions WHERE id=?", (prompt_id,)).fetchone()
    if not row:
        conn.close()
        return False

    name = row["name"]
    conn.execute("UPDATE prompt_versions SET is_active=0 WHERE name=?", (name,))
    conn.execute("UPDATE prompt_versions SET is_active=1 WHERE id=?", (prompt_id,))
    conn.commit()
    conn.close()
    return True


def record_ab_result(
    session_id: int,
    prompt_a_id: int,
    prompt_b_id: int,
    winner: Optional[str] = None,
    metrics: Optional[dict] = None,
) -> dict:
    """Record an A/B comparison result."""
    import json
    conn = get_connection()
    cur = conn.execute(
        """INSERT INTO ab_results (session_id, prompt_a_id, prompt_b_id, winner, metrics)
           VALUES (?, ?, ?, ?, ?)""",
        (session_id, prompt_a_id, prompt_b_id, winner, json.dumps(metrics) if metrics else None),
    )
    conn.commit()
    result = {"id": cur.lastrowid}
    conn.close()
    return result


def list_ab_results(session_id: Optional[int] = None, limit: int = 50) -> list[dict]:
    """List A/B results, optionally filtered by session."""
    conn = get_connection()
    if session_id:
        rows = conn.execute(
            "SELECT * FROM ab_results WHERE session_id=? ORDER BY id DESC LIMIT ?",
            (session_id, limit),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM ab_results ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
    conn.close()
    return [dict(r) for r in rows]

"""
engines/review_queue_engine.py
-------------------------------
Manages the review queue: low-confidence events needing human verification.
Sorted by lowest confidence first (uncertain-first workflow per roadmap).

Maturity: Working Prototype
Future:   Add correction memory, parser benchmark mode (V7).
          Auto-prioritize based on bet size * confidence gap (V10).
"""

from database.db import get_connection


def get_review_queue(session_id: int | None = None, status: str | None = "pending") -> list:
    """
    Return review items. Sorted by confidence ASC (lowest/worst first).
    Filter by session or status if provided.
    """
    conn = get_connection()

    filters = []
    params  = []

    if session_id:
        filters.append("r.session_id = ?")
        params.append(session_id)
    if status:
        filters.append("r.status = ?")
        params.append(status)

    where = ("WHERE " + " AND ".join(filters)) if filters else ""

    rows = conn.execute(
        f"""SELECT r.*, s.name AS session_name, s.game_name,
                   e.bet_amount, e.win_amount, e.balance_after,
                   e.confidence_score, e.timestamp AS event_timestamp
            FROM review_items r
            JOIN sessions s ON s.id = r.session_id
            LEFT JOIN events e ON e.id = r.event_id
            {where}
            ORDER BY e.confidence_score ASC, r.created_at DESC""",
        params
    ).fetchall()

    conn.close()
    return [
        {
            "id":              r["id"],
            "session_id":      r["session_id"],
            "session_name":    r["session_name"],
            "game_name":       r["game_name"],
            "event_id":        r["event_id"],
            "event_timestamp": r["event_timestamp"],
            "bet_amount":      r["bet_amount"],
            "win_amount":      r["win_amount"],
            "balance_after":   r["balance_after"],
            "confidence_score": r["confidence_score"],
            "reason":          r["reason"],
            "status":          r["status"],
            "corrected_value": r["corrected_value"],
            "reviewed_at":     r["reviewed_at"],
            "created_at":      r["created_at"],
        }
        for r in rows
    ]


def resolve_review_item(item_id: int, action: str, corrected_value: str = "") -> bool:
    """
    Accept, reject, or mark an item as corrected.
    action: 'accepted' | 'rejected' | 'corrected'
    Returns True if found and updated.
    """
    valid_actions = {"accepted", "rejected", "corrected"}
    if action not in valid_actions:
        return False

    from datetime import datetime
    conn = get_connection()
    cur = conn.execute(
        "UPDATE review_items SET status = ?, corrected_value = ?, reviewed_at = ? "
        "WHERE id = ?",
        (action, corrected_value, datetime.now().isoformat(), item_id)
    )
    conn.commit()
    conn.close()
    return cur.rowcount > 0


def get_queue_summary() -> dict:
    """Return pending/total counts for dashboard badge."""
    conn = get_connection()
    row = conn.execute("""
        SELECT
            COUNT(*) AS total,
            COUNT(CASE WHEN status='pending'   THEN 1 END) AS pending,
            COUNT(CASE WHEN status='accepted'  THEN 1 END) AS accepted,
            COUNT(CASE WHEN status='rejected'  THEN 1 END) AS rejected,
            COUNT(CASE WHEN status='corrected' THEN 1 END) AS corrected
        FROM review_items
    """).fetchone()
    conn.close()
    return {
        "total":     row["total"],
        "pending":   row["pending"],
        "accepted":  row["accepted"],
        "rejected":  row["rejected"],
        "corrected": row["corrected"],
    }

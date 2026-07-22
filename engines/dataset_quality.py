"""
engines/dataset_quality.py
--------------------------
Dataset quality metrics — completeness, bias, label distribution.
Used for compliance and self-audit.
"""

from __future__ import annotations
from database.db import get_connection


def get_dataset_quality() -> dict:
    """Return dataset quality metrics across all sessions."""
    conn = get_connection()

    total_sessions = conn.execute("SELECT COUNT(*) FROM sessions").fetchone()[0]
    total_events = conn.execute("SELECT COUNT(*) FROM events").fetchone()[0]

    completeness = {}
    for table, columns in [
        ("sessions", ["game_name", "platform", "date", "start_balance", "end_balance", "rtp"]),
        ("events", ["bet_amount", "win_amount", "balance_after", "confidence_score"]),
    ]:
        table_total = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        if table_total == 0:
            completeness[table] = {col: 1.0 for col in columns}
            continue
        for col in columns:
            non_null = conn.execute(
                f"SELECT COUNT(*) FROM {table} WHERE {col} IS NOT NULL AND {col} != ''"
            ).fetchone()[0]
            completeness.setdefault(table, {})[col] = round(non_null / table_total, 4)

    games = [dict(r) for r in conn.execute(
        "SELECT game_name, COUNT(*) as count FROM sessions GROUP BY game_name ORDER BY count DESC"
    ).fetchall()]

    platforms = [dict(r) for r in conn.execute(
        "SELECT platform, COUNT(*) as count FROM sessions GROUP BY platform ORDER BY count DESC"
    ).fetchall()]

    statuses = [dict(r) for r in conn.execute(
        "SELECT status, COUNT(*) as count FROM sessions GROUP BY status ORDER BY count DESC"
    ).fetchall()]

    confidence_buckets = [dict(r) for r in conn.execute("""
        SELECT
            CASE
                WHEN confidence_score >= 0.9 THEN 'high (>=0.9)'
                WHEN confidence_score >= 0.7 THEN 'medium (0.7-0.9)'
                ELSE 'low (<0.7)'
            END as bucket,
            COUNT(*) as count
        FROM events
        GROUP BY bucket
        ORDER BY bucket
    """).fetchall()]

    monthly = [dict(r) for r in conn.execute(
        "SELECT strftime('%Y-%m', date) as month, COUNT(*) as count "
        "FROM sessions GROUP BY month ORDER BY month DESC LIMIT 12"
    ).fetchall()]

    net_stats = dict(conn.execute(
        "SELECT ROUND(AVG(net_result),2) as avg, ROUND(MIN(net_result),2) as min, "
        "ROUND(MAX(net_result),2) as max, ROUND(AVG(rtp),2) as avg_rtp FROM sessions"
    ).fetchone() or {})

    conn.close()

    return {
        "total_sessions": total_sessions,
        "total_events": total_events,
        "completeness": completeness,
        "game_distribution": games,
        "platform_distribution": platforms,
        "status_distribution": statuses,
        "confidence_distribution": confidence_buckets,
        "monthly_activity": monthly,
        "net_result_stats": net_stats,
    }
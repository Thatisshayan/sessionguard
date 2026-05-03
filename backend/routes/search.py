"""
backend/routes/search.py
-------------------------
Global search across sessions, insights, alerts, notes.
One endpoint — multiple result types returned together.
Maturity: Working Prototype
"""

from fastapi import APIRouter, Query
from database.db import get_connection

router = APIRouter(tags=["search"])


@router.get("/search")
def global_search(
    q:     str = Query(..., min_length=1, max_length=200),
    limit: int = Query(20, le=100),
):
    """
    Search sessions, insights, alerts, and notes in one call.
    Returns grouped results with type labels.
    """
    term  = f"%{q}%"
    conn  = get_connection()
    results = []

    # Sessions — match name, game_name, platform, notes
    sessions = conn.execute("""
        SELECT id, name, game_name, platform, date, net_result, rtp, status
        FROM sessions
        WHERE name LIKE ? OR game_name LIKE ? OR platform LIKE ? OR notes LIKE ?
        ORDER BY date DESC LIMIT ?
    """, (term, term, term, term, limit)).fetchall()
    for r in sessions:
        results.append({
            "type":    "session",
            "id":      r["id"],
            "title":   r["name"],
            "subtitle": f"{r['game_name']} · {r['platform']} · {r['date']}",
            "meta":    {"net_result": r["net_result"], "rtp": r["rtp"], "status": r["status"]},
            "url":     f"/sessions/{r['id']}",
        })

    # Insights — match text
    insights = conn.execute("""
        SELECT i.id, i.session_id, i.text, i.severity, s.name AS session_name
        FROM insights i JOIN sessions s ON s.id = i.session_id
        WHERE i.text LIKE ?
        ORDER BY i.created_at DESC LIMIT ?
    """, (term, limit)).fetchall()
    for r in insights:
        results.append({
            "type":    "insight",
            "id":      r["id"],
            "title":   r["text"][:80],
            "subtitle": f"{r['session_name']} · {r['severity']}",
            "meta":    {"session_id": r["session_id"], "severity": r["severity"]},
            "url":     f"/sessions/{r['session_id']}",
        })

    # Alerts — match message
    alerts = conn.execute("""
        SELECT a.id, a.session_id, a.message, a.severity, s.name AS session_name
        FROM alerts a JOIN sessions s ON s.id = a.session_id
        WHERE a.message LIKE ?
        ORDER BY a.created_at DESC LIMIT ?
    """, (term, limit)).fetchall()
    for r in alerts:
        results.append({
            "type":    "alert",
            "id":      r["id"],
            "title":   r["message"][:80],
            "subtitle": f"{r['session_name']} · {r['severity']}",
            "meta":    {"session_id": r["session_id"], "severity": r["severity"]},
            "url":     f"/sessions/{r['session_id']}",
        })

    # Notes — match note text
    notes = conn.execute("""
        SELECT n.id, n.session_id, n.note, n.version, s.name AS session_name
        FROM session_notes n JOIN sessions s ON s.id = n.session_id
        WHERE n.note LIKE ?
        ORDER BY n.created_at DESC LIMIT ?
    """, (term, limit)).fetchall()
    for r in notes:
        results.append({
            "type":    "note",
            "id":      r["id"],
            "title":   r["note"][:80],
            "subtitle": f"{r['session_name']} · v{r['version']}",
            "meta":    {"session_id": r["session_id"]},
            "url":     f"/sessions/{r['session_id']}",
        })

    conn.close()

    # Group by type for UI
    grouped = {}
    for r in results:
        grouped.setdefault(r["type"], []).append(r)

    return {
        "query":        q,
        "total":        len(results),
        "grouped":      grouped,
        "results":      results[:limit],
    }

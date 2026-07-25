"""
backend/routes/search.py
-------------------------
Global search across sessions, insights, alerts, notes.
One endpoint — multiple result types returned together.
Maturity: Working Prototype
"""

from fastapi import APIRouter, Query, Header
from database.db import get_connection, async_fetch_all
from backend.auth.access import require_current_user

router = APIRouter(tags=["search"])


@router.get("/search")
async def global_search(
    q:     str = Query(..., min_length=1, max_length=200),
    limit: int = Query(20, le=100),
    authorization: str | None = Header(None, alias="Authorization"),
):
    """
    Search sessions, insights, alerts, and notes in one call.
    Returns grouped results with type labels.
    """
    term  = f"%{q}%"
    results = []
    current_user = require_current_user(authorization)

    access_clause = ""
    access_params: list[int] = []
    if current_user["role"] != "admin":
        access_clause = """
            AND (
                s.owner_id = ?
                OR EXISTS (
                    SELECT 1
                    FROM session_projects sp
                    JOIN project_members pm ON pm.project_id = sp.project_id
                    WHERE sp.session_id = s.id AND pm.user_id = ?
                )
            )
        """
        access_params = [current_user["user_id"], current_user["user_id"]]

    # Sessions — match name, game_name, platform, notes
    sessions = await async_fetch_all(f"""
        SELECT s.id, s.name, s.game_name, s.platform, s.date, s.net_result, s.rtp, s.status
        FROM sessions s
        WHERE (s.name LIKE ? OR s.game_name LIKE ? OR s.platform LIKE ? OR s.notes LIKE ?)
        {access_clause}
        ORDER BY s.date DESC LIMIT ?
    """, (term, term, term, term, *access_params, limit))
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
    insights = await async_fetch_all(f"""
        SELECT i.id, i.session_id, i.text, i.severity, s.name AS session_name
        FROM insights i JOIN sessions s ON s.id = i.session_id
        WHERE i.text LIKE ?
        {access_clause}
        ORDER BY i.created_at DESC LIMIT ?
    """, (term, *access_params, limit))
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
    alerts = await async_fetch_all(f"""
        SELECT a.id, a.session_id, a.message, a.severity, s.name AS session_name
        FROM alerts a JOIN sessions s ON s.id = a.session_id
        WHERE a.message LIKE ?
        {access_clause}
        ORDER BY a.created_at DESC LIMIT ?
    """, (term, *access_params, limit))
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
    notes = await async_fetch_all(f"""
        SELECT n.id, n.session_id, n.note, n.version, s.name AS session_name
        FROM session_notes n JOIN sessions s ON s.id = n.session_id
        WHERE n.note LIKE ?
        {access_clause}
        ORDER BY n.created_at DESC LIMIT ?
    """, (term, *access_params, limit))
    for r in notes:
        results.append({
            "type":    "note",
            "id":      r["id"],
            "title":   r["note"][:80],
            "subtitle": f"{r['session_name']} · v{r['version']}",
            "meta":    {"session_id": r["session_id"]},
            "url":     f"/sessions/{r['session_id']}",
        })

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

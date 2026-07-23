"""
backend/routes/intelligence.py
-------------------------------
V12: Clustering, anomalies, peer benchmarking, dataset summary.
V13: NVIDIA AI insights, narrative, comparison, review suggestions.
All in one file — intelligence layer.
Maturity: Working Prototype
"""

from fastapi import APIRouter, HTTPException, Query, Header
from pydantic import BaseModel
from typing import Optional

router = APIRouter(tags=["intelligence"])


# ── V12: Clustering ────────────────────────────────────────────────────────────

@router.post("/intelligence/clusters/build")
def build_clusters(threshold: float = Query(0.88, ge=0.5, le=1.0)):
    """Build session clusters. Run after importing new sessions."""
    from engines.cluster_engine import build_clusters
    return build_clusters(threshold)


@router.get("/intelligence/clusters")
async def get_clusters():
    """Return existing cluster assignments from DB."""
    from database.db import async_fetch_all
    rows = await async_fetch_all("""
        SELECT sc.cluster_label, sc.session_id, sc.similarity_score,
               s.name, s.game_name, s.rtp, s.net_result, s.date
        FROM session_clusters sc JOIN sessions s ON s.id = sc.session_id
        ORDER BY sc.cluster_label, sc.similarity_score DESC
    """)
    clusters: dict = {}
    for r in rows:
        d = dict(r)
        label = d.pop("cluster_label")
        clusters.setdefault(label, []).append(d)
    return {"cluster_count": len(clusters), "clusters": clusters}


@router.get("/intelligence/clusters/session/{session_id}")
def session_cluster(session_id: int):
    """Which cluster does this session belong to?"""
    from engines.cluster_engine import get_session_cluster
    c = get_session_cluster(session_id)
    if not c:
        raise HTTPException(status_code=404,
                            detail="Session not clustered yet. Run /intelligence/clusters/build first.")
    return c


@router.get("/intelligence/benchmark/{session_id}")
def peer_benchmark(session_id: int):
    """Compare session against its cluster peers."""
    from engines.cluster_engine import peer_benchmark
    r = peer_benchmark(session_id)
    if r.get("status") == "no_peers":
        raise HTTPException(status_code=422, detail="No peers found. Build clusters first.")
    return r


@router.get("/intelligence/dataset-summary")
def dataset_summary():
    """Aggregate risk summary across all sessions."""
    from engines.cluster_engine import get_dataset_summary
    r = get_dataset_summary()
    if r.get("status") == "no_data":
        raise HTTPException(status_code=404, detail="No sessions found.")
    return r


@router.get("/intelligence/anomalies")
def anomalies(z_threshold: float = Query(2.0, ge=1.0, le=4.0)):
    """Flag statistically anomalous sessions."""
    from engines.cluster_engine import detect_anomalies
    return detect_anomalies(z_threshold)


# ── V13: AI insights ───────────────────────────────────────────────────────────

@router.get("/intelligence/ai/status")
def ai_status():
    """Check if NVIDIA AI is available and configured."""
    from engines.ai_insights_engine import get_ai_status
    return get_ai_status()


@router.get("/intelligence/ai/session/{session_id}")
def ai_session_narrative(
    session_id:     int,
    force_refresh:  bool = Query(False),
):
    """
    Generate an AI narrative analysis for a session.
    Falls back to rule-based if API key not set.
    """
    from engines.ai_insights_engine import generate_session_narrative
    result = generate_session_narrative(session_id, force_refresh)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


class CompareRequest(BaseModel):
    session_ids: list[int]


@router.post("/intelligence/ai/compare")
def ai_compare(body: CompareRequest):
    """Generate AI comparison narrative across multiple sessions."""
    if len(body.session_ids) < 2:
        raise HTTPException(status_code=400, detail="Need at least 2 session IDs.")
    from engines.ai_insights_engine import generate_comparison_narrative
    return generate_comparison_narrative(body.session_ids)


@router.get("/intelligence/ai/review/{review_item_id}")
def ai_review_suggestion(review_item_id: int):
    """Get AI suggestion for a review item (accept/reject + reasoning)."""
    from engines.ai_insights_engine import suggest_review_resolution
    result = suggest_review_resolution(review_item_id)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result

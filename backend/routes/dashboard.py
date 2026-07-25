"""
backend/routes/dashboard.py
----------------------------
Aggregated dashboard endpoint — single call replaces 9 parallel fetches.
"""

import asyncio
from fastapi import APIRouter, Header
from typing import Optional
from backend.auth.access import require_admin
from engines.analysis_engine import (
    get_global_metrics,
    get_rtp_distribution,
    get_net_result_over_time,
)
from engines.insights_engine import get_insights
from engines.alerts_engine import get_alerts, get_alert_summary
from engines.review_queue_engine import get_review_queue, get_queue_summary
from engines.behavior_engine import analyze_behavior_global

router = APIRouter(tags=["dashboard"])


@router.get("/summary")
async def dashboard_summary(authorization: Optional[str] = Header(None, alias="Authorization")):
    """
    Single aggregated response for the Dashboard page.
    Returns all KPIs, charts, insights, alerts, queue, and behavior data.
    """
    await require_admin(authorization)
    metrics, net, rtp, insights, alerts, alert_summary, queue, queue_summary, behavior = await asyncio.gather(
        asyncio.to_thread(get_global_metrics),
        asyncio.to_thread(get_net_result_over_time),
        asyncio.to_thread(get_rtp_distribution),
        asyncio.to_thread(get_insights, limit=50),
        asyncio.to_thread(get_alerts, unacknowledged_only=True),
        asyncio.to_thread(get_alert_summary),
        asyncio.to_thread(get_review_queue, status="pending"),
        asyncio.to_thread(get_queue_summary),
        asyncio.to_thread(analyze_behavior_global),
    )
    return {
        "metrics":         metrics,
        "net_over_time":   net,
        "rtp_distribution": rtp,
        "insights":        insights,
        "alerts":          alerts,
        "alert_summary":   alert_summary,
        "review_queue":    queue,
        "queue_summary":   queue_summary,
        "behavior":        behavior,
    }

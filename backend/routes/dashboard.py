"""
backend/routes/dashboard.py
----------------------------
Aggregated dashboard endpoint — single call replaces 9 parallel fetches.
"""

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
def dashboard_summary(authorization: Optional[str] = Header(None, alias="Authorization")):
    """
    Single aggregated response for the Dashboard page.
    Returns all KPIs, charts, insights, alerts, queue, and behavior data.
    """
    require_admin(authorization)
    return {
        "metrics":         get_global_metrics(),
        "net_over_time":   get_net_result_over_time(),
        "rtp_distribution": get_rtp_distribution(),
        "insights":        get_insights(limit=50),
        "alerts":          get_alerts(unacknowledged_only=True),
        "alert_summary":   get_alert_summary(),
        "review_queue":    get_review_queue(status="pending"),
        "queue_summary":   get_queue_summary(),
        "behavior":        analyze_behavior_global(),
    }

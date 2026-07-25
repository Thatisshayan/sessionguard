"""
backend/routes/metrics.py
--------------------------
Aggregate KPI endpoints. Delegates entirely to analysis_engine.
"""

from fastapi import APIRouter, Header
from typing import Optional
from backend.auth.access import require_admin
from engines.analysis_engine import (
    get_global_metrics,
    get_rtp_distribution,
    get_net_result_over_time,
    get_performance_by_game,
)

router = APIRouter(tags=["metrics"])


@router.get("")
def global_metrics(authorization: Optional[str] = Header(None, alias="Authorization")):
    """Dashboard KPI strip — platform-wide aggregates."""
    require_admin(authorization)
    return get_global_metrics()


@router.get("/rtp-distribution")
def rtp_distribution(authorization: Optional[str] = Header(None, alias="Authorization")):
    """Session count bucketed by RTP range. Used for histogram charts."""
    require_admin(authorization)
    return get_rtp_distribution()


@router.get("/net-over-time")
def net_over_time(authorization: Optional[str] = Header(None, alias="Authorization")):
    """Cumulative net result by date. Used for line/area charts."""
    require_admin(authorization)
    return get_net_result_over_time()


@router.get("/by-game")
def performance_by_game(authorization: Optional[str] = Header(None, alias="Authorization")):
    """Avg RTP and net result grouped by game name."""
    require_admin(authorization)
    return get_performance_by_game()

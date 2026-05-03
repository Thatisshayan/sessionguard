"""
backend/routes/metrics.py
--------------------------
Aggregate KPI endpoints. Delegates entirely to analysis_engine.
"""

from fastapi import APIRouter
from engines.analysis_engine import (
    get_global_metrics,
    get_rtp_distribution,
    get_net_result_over_time,
    get_performance_by_game,
)

router = APIRouter(tags=["metrics"])


@router.get("")
def global_metrics():
    """Dashboard KPI strip — platform-wide aggregates."""
    return get_global_metrics()


@router.get("/rtp-distribution")
def rtp_distribution():
    """Session count bucketed by RTP range. Used for histogram charts."""
    return get_rtp_distribution()


@router.get("/net-over-time")
def net_over_time():
    """Cumulative net result by date. Used for line/area charts."""
    return get_net_result_over_time()


@router.get("/by-game")
def performance_by_game():
    """Avg RTP and net result grouped by game name."""
    return get_performance_by_game()

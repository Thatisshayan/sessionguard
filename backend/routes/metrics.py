"""
backend/routes/metrics.py
--------------------------
Aggregate KPI endpoints. Delegates entirely to analysis_engine.
"""

import asyncio
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
async def global_metrics(authorization: Optional[str] = Header(None, alias="Authorization")):
    """Dashboard KPI strip — platform-wide aggregates."""
    await require_admin(authorization)
    return await asyncio.to_thread(get_global_metrics)


@router.get("/rtp-distribution")
async def rtp_distribution(authorization: Optional[str] = Header(None, alias="Authorization")):
    """Session count bucketed by RTP range. Used for histogram charts."""
    await require_admin(authorization)
    return await asyncio.to_thread(get_rtp_distribution)


@router.get("/net-over-time")
async def net_over_time(authorization: Optional[str] = Header(None, alias="Authorization")):
    """Cumulative net result by date. Used for line/area charts."""
    await require_admin(authorization)
    return await asyncio.to_thread(get_net_result_over_time)


@router.get("/by-game")
async def performance_by_game(authorization: Optional[str] = Header(None, alias="Authorization")):
    """Avg RTP and net result grouped by game name."""
    await require_admin(authorization)
    return await asyncio.to_thread(get_performance_by_game)

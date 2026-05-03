"""
backend/middleware/rate_limit.py
---------------------------------
Simple sliding-window rate limiter using stdlib only.
No slowapi/redis needed for local-first builds.

Usage in routes:
    from backend.middleware.rate_limit import check_rate_limit
    check_rate_limit(client_ip, "login", max_calls=5, window_seconds=60)

Maturity: Working Prototype
Future:   Replace with Redis-backed distributed limiter for SaaS (V7+).
"""

from __future__ import annotations
import time
import threading
from collections import defaultdict, deque

_LOCK    = threading.Lock()
_WINDOWS : dict[str, deque] = defaultdict(deque)

# Default limits per endpoint category
LIMITS = {
    "login":    (5,  60),    # 5 attempts per 60 seconds
    "signup":   (3,  300),   # 3 per 5 minutes
    "refresh":  (20, 60),    # 20 per minute
    "upload":   (30, 60),    # 30 uploads per minute
    "export":   (20, 60),    # 20 exports per minute
    "api":      (200, 60),   # 200 general API calls per minute
    "benchmark":(10, 60),    # 10 benchmark runs per minute
}


def check_rate_limit(
    client_id:      str,
    category:       str = "api",
    max_calls:      int | None = None,
    window_seconds: int | None = None,
) -> dict:
    """
    Check if client_id has exceeded the rate limit for category.
    Returns {"allowed": bool, "remaining": int, "reset_in": float}
    """
    default_max, default_window = LIMITS.get(category, (200, 60))
    max_c  = max_calls      or default_max
    window = window_seconds or default_window

    now    = time.monotonic()
    key    = f"{client_id}:{category}"

    with _LOCK:
        q = _WINDOWS[key]
        # Drop entries outside window
        cutoff = now - window
        while q and q[0] < cutoff:
            q.popleft()

        remaining = max_c - len(q)
        allowed   = remaining > 0

        if allowed:
            q.append(now)
            remaining -= 1

        reset_in = (q[0] + window - now) if q else 0.0

    return {
        "allowed":   allowed,
        "remaining": max(remaining, 0),
        "reset_in":  round(reset_in, 1),
        "limit":     max_c,
        "window":    window,
    }


def rate_limit_headers(result: dict) -> dict:
    """Return HTTP headers for rate limit info."""
    return {
        "X-RateLimit-Limit":     str(result["limit"]),
        "X-RateLimit-Remaining": str(result["remaining"]),
        "X-RateLimit-Reset":     str(int(result["reset_in"])),
    }


def get_client_ip(request) -> str:
    """Extract client IP from FastAPI Request object."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return getattr(getattr(request, "client", None), "host", "unknown")

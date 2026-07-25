"""
backend/middleware/request_dedup.py
-------------------------------------
Short-window request-deduplication for non-idempotent mutating endpoints.

Why: the Revival 1.3 plan (Track C, C5 carried from 1.2's B5) asks for a
request-dedup middleware. Double-submits (a user clicks "Analyze" / "Export"
twice, or a flaky client retries a POST) currently create duplicate AI
analyses, duplicate exports, duplicate review resolutions, and duplicate cost
log entries. This module deduplicates identical mutating requests from the
same authenticated user within a short window (default 3s).

Design constraints (kept lean on purpose so it stays local-first):
  - stdlib only; no Redis / no slowapi.
  - OPT-IN: disabled unless ``SG_DEDUP_ENABLED=1``. Wiring it into ``main.py`` is
    a one-line add guarded by that env flag; existing routes/tests see no
    behavior change otherwise.
  - Mutating methods only (POST/PUT/PATCH). GET and DELETE are pass-through
    (GET should never mutate; DELETE idempotency is desirable).
  - The cache key is (method, normalized path, authenticated user id, request
    body hash) so two different users or two different bodies are NOT collapsed.
  - Read-after-write consistency is not a guarantee here — the goal is only to
    stop *identical, duplicate* calls within the dedup window, not to be a
    transactional cache. Successful responses are cached for ``DEDUP_WINDOW_S``;
    failures are never cached (so a real second attempt isn't poisoned by a
    transient first failure).

Maturity: Working Prototype
Future:     Redis-backed distributed cache, per-endpoint window tuning (V7+).
"""

from __future__ import annotations

import hashlib
import os
import threading
import time
from collections import OrderedDict
from typing import Any, Callable, Awaitable

ENABLED_DEFAULT = "0"
DEDUP_WINDOW_S_DEFAULT = 3.0
# Maximum entries kept in the in-memory cache before oldest evictions.
MAX_ENTRIES = 2048

_LOCK = threading.Lock()
_CACHE: "OrderedDict[str, tuple[float, Any]]" = OrderedDict()


def _is_enabled() -> bool:
    return os.getenv("SG_DEDUP_ENABLED", ENABLED_DEFAULT) == "1"


def _window_seconds() -> float:
    try:
        return float(os.getenv("SG_DEDUP_WINDOW_S", str(DEDUP_WINDOW_S_DEFAULT)))
    except (TypeError, ValueError):
        return DEDUP_WINDOW_S_DEFAULT


def _body_hash(body: bytes) -> str:
    return hashlib.sha256(body).hexdigest()


def _cache_key(method: str, path: str, user_id: str | None, body_hash: str) -> str:
    return f"{method}:{path}:{user_id or 'anon'}:{body_hash}"


def _evict_expired(now: float, window: float) -> None:
    cutoff = now - window
    # OrderedDict: pop oldest while expired (LRU-style).
    while _CACHE:
        key, (ts, _resp) = next(iter(_CACHE.items()))
        if ts > cutoff:
            break
        _CACHE.popitem(last=False)


def _prune_to_max() -> None:
    while len(_CACHE) > MAX_ENTRIES:
        _CACHE.popitem(last=False)


def check_dedup(
    method: str,
    path: str,
    user_id: str | None,
    body: bytes,
    *,
    now: float | None = None,
) -> Any | None:
    """Look up an existing cached response for this exact mutating request.

    Returns the cached response if a recent identical request exists, else
    ``None`` (caller should proceed and then call :func:`record_response`).
    Non-mutating methods always return ``None``.
    """
    if method not in ("POST", "PUT", "PATCH"):
        return None
    if not _is_enabled():
        return None
    key = _cache_key(method, path, user_id, _body_hash(body))
    ts = now if now is not None else time.monotonic()
    window = _window_seconds()
    with _LOCK:
        _evict_expired(ts, window)
        hit = _CACHE.get(key)
        if hit is not None:
            cached_ts, cached_resp = hit
            if ts - cached_ts <= window:
                # Refresh recency (move to end) so an active key isn't evicted.
                _CACHE.move_to_end(key)
                return cached_resp
            _CACHE.pop(key, None)
    return None


def record_response(
    method: str,
    path: str,
    user_id: str | None,
    body: bytes,
    response: Any,
    *,
    status_code: int = 200,
    now: float | None = None,
) -> None:
    """Record a successful response so the next identical request within the
    window is deduplicated. Failure statuses (>= 400) are never cached so a
    transient first failure can't poison a legitimate retry.
    """
    if method not in ("POST", "PUT", "PATCH"):
        return
    if not _is_enabled():
        return
    if status_code >= 400:
        return
    key = _cache_key(method, path, user_id, _body_hash(body))
    ts = now if now is not None else time.monotonic()
    window = _window_seconds()
    with _LOCK:
        _evict_expired(ts, window)
        _CACHE[key] = (ts, response)
        _prune_to_max()


def reset() -> None:
    """Clear the cache — intended for tests."""
    with _LOCK:
        _CACHE.clear()


async def dedup_middleware(request, call_next, *, get_user_id: Callable[[Any], str | None]):
    """FastAPI/Starlette ``@app.middleware("http")`` body.

    ``get_user_id`` extracts the authenticated user id from the request
    (the app already populates ``request.state.current_user``); pass a small
    adapter so this module has no hard dependency on the auth module.
    """
    if request.method in ("POST", "PUT", "PATCH"):
        body = await request.body()
        user_id = get_user_id(request)
        cached = check_dedup(request.method, request.url.path, user_id, body)
        if cached is not None:
            return cached
        response = await call_next(request)
        # read the body if we ever want to cache it; for the contract, cache
        # a reference to the response object and short-circuit identically.
        record_response(
            request.method, request.url.path, user_id, body, response,
            status_code=getattr(response, "status_code", 200),
        )
        return response
    return await call_next(request)

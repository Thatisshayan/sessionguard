"""Contract tests for backend/middleware/request_dedup.py (Revival 1.3, C5).

C5 (carried from 1.2 B5) asked for a request-dedup middleware. These tests
pin the contract without wiring it into main.py by default (it's opt-in via
``SG_DEDUP_ENABLED=1``), so the existing 190-test suite sees zero behavior
change while the dedup logic itself is regression-locked.
"""

from __future__ import annotations

import os

import pytest

from backend.middleware import request_dedup as dedup


@pytest.fixture(autouse=True)
def _isolate_dedup(monkeypatch):
    """Every test enables dedup, then clears cache + env override at teardown."""
    monkeypatch.setenv("SG_DEDUP_ENABLED", "1")
    monkeypatch.setenv("SG_DEDUP_WINDOW_S", "2.0")
    dedup.reset()
    yield
    dedup.reset()


def test_disabled_by_default_returns_no_hit(monkeypatch):
    monkeypatch.setenv("SG_DEDUP_ENABLED", "0")
    dedup.reset()
    body = b'{"x": 1}'
    # First call records, second would normally hit — but with dedup disabled
    # it must return None both times (no caching occurs).
    assert dedup.check_dedup("POST", "/api/v1/a", "u1", body) is None
    dedup.record_response("POST", "/api/v1/a", "u1", body, {"ok": True}, status_code=200)
    assert dedup.check_dedup("POST", "/api/v1/a", "u1", body) is None


class TestMutatingDedup:
    def test_second_identical_post_returns_cached_response(self):
        body = b'{"session_id": 7}'
        assert dedup.check_dedup("POST", "/api/v1/sessions/7/ai", "u1", body) is None
        cached = {"source": "nvidia_ai", "ok": True}
        dedup.record_response(
            "POST", "/api/v1/sessions/7/ai", "u1", body, cached, status_code=200
        )
        assert dedup.check_dedup("POST", "/api/v1/sessions/7/ai", "u1", body) is cached

    def test_put_and_patch_are_deduped_but_get_and_delete_are_not(self):
        body = b'{"v": 1}'
        for method in ("PUT", "PATCH"):
            assert dedup.check_dedup(method, "/api/v1/r", "u", body) is None
            resp = {"m": method}
            dedup.record_response(method, "/api/v1/r", "u", body, resp, status_code=200)
            assert dedup.check_dedup(method, "/api/v1/r", "u", body) is resp
        for method in ("GET", "DELETE", "HEAD"):
            # mutating-only set: record is a no-op; check returns None even if
            # we forced a record before (which we don't).
            assert dedup.check_dedup(method, "/api/v1/r", "u", body) is None

    def test_different_users_are_not_deduped_together(self):
        body = b'{"a": 1}'
        dedup.record_response("POST", "/api/v1/x", "userA", body, {"u": "A"}, status_code=200)
        assert dedup.check_dedup("POST", "/api/v1/x", "userB", body) is None
        assert dedup.check_dedup("POST", "/api/v1/x", "userA", body) == {"u": "A"}

    def test_different_bodies_are_not_deduped_together(self):
        dedup.record_response("POST", "/api/v1/x", "u", b'{"a": 1}', {"v": 1}, status_code=200)
        assert dedup.check_dedup("POST", "/api/v1/x", "u", b'{"a": 2}') is None

    def test_different_paths_are_not_deduped_together(self):
        body = b'{"a": 1}'
        dedup.record_response("POST", "/api/v1/x", "u", body, {"v": 1}, status_code=200)
        assert dedup.check_dedup("POST", "/api/v1/y", "u", body) is None


class TestFailureAndExpiry:
    def test_failure_statuses_are_never_cached(self):
        body = b'{"a": 1}'
        dedup.record_response("POST", "/api/v1/x", "u", body, {"err": "boom"},
                              status_code=500)
        # A 5xx must not poison the retry.
        assert dedup.check_dedup("POST", "/api/v1/x", "u", body) is None

        dedup.record_response("POST", "/api/v1/x", "u", body, {"err": "bad"},
                              status_code=400)
        # A 4xx must not be cached either.
        assert dedup.check_dedup("POST", "/api/v1/x", "u", body) is None

    def test_expired_entries_are_evicted_and_miss(self):
        body = b'{"a": 1}'
        # Record at t0.
        dedup.record_response("POST", "/api/v1/x", "u", body, {"ok": True},
                              status_code=200, now=0.0)
        # Within the 2s window -> hit.
        assert dedup.check_dedup("POST", "/api/v1/x", "u", body, now=1.5) == {"ok": True}
        # After the window -> miss and the stale entry is evicted.
        assert dedup.check_dedup("POST", "/api/v1/x", "u", body, now=3.0) is None

    def test_active_key_renewed_by_recency_not_evicted(self):
        body = b'{"a": 1}'
        dedup.record_response("POST", "/api/v1/hot", "u", body, {"ok": True}, now=0.0)
        # Repeatedly hit at rising timestamps within the 2s window so the key
        # is move_to_end'd each time; it must still hit at t=1.9.
        for t in (0.5, 1.0, 1.5, 1.9):
            assert dedup.check_dedup("POST", "/api/v1/hot", "u", body, now=t) == {"ok": True}


class TestCacheBounds:
    def test_max_entries_eviction_is_oldest_first(self, monkeypatch):
        # Shrink the cache so eviction is observable.
        monkeypatch.setattr(dedup, "MAX_ENTRIES", 3)
        dedup.reset()
        bodies = [b'{"k":1}', b'{"k":2}', b'{"k":3}']
        for i, b in enumerate(bodies):
            dedup.record_response("POST", "/api/v1/x", "u", b, {"i": i}, now=0.0)
        # Adding a 4th evicts the oldest ({"k":1}).
        dedup.record_response("POST", "/api/v1/x", "u", b'{"k":4}', {"i": 3}, now=0.0)
        # Use the same synthetic now= so the 2s window doesn't expire the rest.
        assert dedup.check_dedup("POST", "/api/v1/x", "u", b'{"k":1}', now=1.0) is None
        assert dedup.check_dedup("POST", "/api/v1/x", "u", b'{"k":2}', now=1.0) == {"i": 1}
        assert dedup.check_dedup("POST", "/api/v1/x", "u", b'{"k":4}', now=1.0) == {"i": 3}


def test_invalid_window_falls_back_to_default(monkeypatch):
    monkeypatch.setenv("SG_DEDUP_WINDOW_S", "not-a-number")
    dedup.reset()
    # Should not raise; window falls back to the 3s default.
    body = b'{"a": 1}'
    dedup.record_response("POST", "/api/v1/x", "u", body, {"ok": True}, now=0.0)
    assert dedup.check_dedup("POST", "/api/v1/x", "u", body, now=1.0) == {"ok": True}


@pytest.mark.asyncio
async def test_dedup_middleware_short_circuits_double_post():
    """End-to-end: the middleware wrapper itself returns the cached response on
    the second identical mutating request and passes GETs through unmodified."""
    from starlette.requests import Request
    from starlette.responses import JSONResponse

    body = b'{"a": 1}'
    call_count = {"n": 0}

    async def app_inner(_req):
        call_count["n"] += 1
        return JSONResponse({"served_by": "app", "call": call_count["n"]}, status_code=200)

    def make_request(method: str, _body: bytes) -> Request:
        scope = {"type": "http", "method": method, "path": "/api/v1/x",
                 "headers": [], "query_string": b"", "raw_path": b"/api/v1/x"}
        request = Request(scope)

        async def _receive():
            return {"type": "http.request", "body": _body, "more_body": False}

        request._receive = _receive  # type: ignore[attr-defined]
        return request

    def _get_user_id(_request):
        return "u1"

    # First POST -> app runs, response recorded.
    req1 = make_request("POST", body)
    resp1 = await dedup.dedup_middleware(req1, app_inner, get_user_id=_get_user_id)
    assert resp1.status_code == 200
    assert call_count["n"] == 1

    # Second identical POST -> dedup short-circuits, app NOT called again.
    req2 = make_request("POST", body)
    resp2 = await dedup.dedup_middleware(req2, app_inner, get_user_id=_get_user_id)
    assert resp2 is resp1
    assert call_count["n"] == 1

    # A GET passes through always — app IS called (dedup ignores GETs).
    req3 = make_request("GET", body)
    await dedup.dedup_middleware(req3, app_inner, get_user_id=_get_user_id)
    assert call_count["n"] == 2

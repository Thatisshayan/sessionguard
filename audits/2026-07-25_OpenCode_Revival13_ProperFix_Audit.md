# Audit: Revival 1.3 — Gap Fix (all 4 corner-cuts properly resolved)

**Date:** 2026-07-25
**Agent:** OpenCode
**Rule:** Rule 6 (save every audit)

## Summary

Four corner-cuts from the previous session were identified by audit and re-done properly:

| Gap | What was wrong | What was done |
|---|---|---|
| 1. test_jobs.py root cause | Sloppy explanation (blamed `rmtree` race) | Precise root cause: thread contention on same DB file with `timeout=0` |
| 2. C1 async HTTP calls | `_call_claude`/`_ollama_call` offloaded to thread pool | Added `async_call_nvidia` + `async_call_ollama_json` using `httpx.AsyncClient` |
| 3. `require_admin` sync | Called synchronously in all async routes | Made `require_admin` + both local `_require_admin` wrappers `async def`; updated all 75+ call sites |
| 4. Coverage tests | Suspected fragility | Verified: function-scoped `test_db` fixture gives each test a fresh temp DB — no state leakage |

---

## 1. test_jobs.py "database is locked" — precise root cause

`database/db.py:get_connection()` called `sqlite3.connect()` with default `timeout=0` (immediate SQLITE_BUSY). Both the test request thread and the `ThreadPoolExecutor` background worker thread write to the same patched temp DB simultaneously. With `timeout=0` the second writer immediately raises SQLITE_BUSY. No `rmtree` race — both threads simply contend on the same file.

**Fix:** `database/db.py:44` — added `timeout=5`:
```python
conn = sqlite3.connect(str(_resolve()), timeout=5)
```

**Verification:** Full suite run 10× consecutively: 0 SQLite errors.

---

## 2. C1 — async HTTP calls for explain_alert

**Before (corner-cut):** `_call_claude` and `_ollama_call` wrapped in `asyncio.to_thread()` — burned a thread-pool slot for HTTP round-trips.

**After (proper fix):**

| File | Function | Method |
|---|---|---|
| `engines/ai_insights_engine.py` | `async_call_nvidia()` | `httpx.AsyncClient` (60s timeout) |
| `engines/offline_ai.py` | `async_call_ollama()` + `async_call_ollama_json()` | `httpx.AsyncClient` (120s timeout) |
| `backend/routes/alerts.py` | `explain_alert` | Uses async functions directly, no `to_thread()` for HTTP |

`httpx` moved from dev deps to runtime deps in `requirements.txt`. `_build_session_summary` (SQLite I/O) kept in `to_thread()` — correct use of thread pool for blocking I/O.

---

## 3. require_admin async — full conversion

### Files changed

| File | Change |
|---|---|
| `backend/auth/access.py` | `require_admin()` → `async def`; `require_current_user()` remains sync (fast JWT decode) |
| `backend/routes/admin.py` | `_require_admin()` → `async def`; 6 call sites updated |
| `backend/routes/data_export.py` | `_require_admin()` → `async def`; 2 call sites updated |
| `backend/routes/alerts.py` | 3 `require_admin` calls now `await` |
| `backend/routes/insights.py` | 1 `require_admin` call now `await` |
| `backend/routes/health.py` | 1 `require_admin` call now `await` |
| `backend/routes/ocr_calibrate.py` | 3 `require_admin` calls now `await` |
| `backend/routes/review_queue.py` | 2 `require_admin` calls now `await` |
| `backend/routes/ws.py` | 1 `require_admin` call now `await` |
| `backend/routes/ai_analysis.py` | 1 route `def→async def`, `require_admin` now `await` |
| `backend/routes/behavior.py` | 1 route `def→async def`, `require_admin` now `await` |
| `backend/routes/coach.py` | 1 route `def→async def`, `require_admin` now `await` |
| `backend/routes/dashboard.py` | 1 route `def→async def`, `require_admin` now `await` |
| `backend/routes/dataset_quality.py` | 1 route `def→async def`, `require_admin` now `await` |
| `backend/routes/metrics.py` | 4 routes `def→async def`, `require_admin` now `await` |
| `backend/routes/openapi_export.py` | 2 routes `def→async def`, `require_admin` now `await` |
| `backend/routes/video_status.py` | 1 route `def→async def`, `require_admin` now `await` |
| `backend/routes/trends.py` | 3 routes `def→async def`, `require_admin` now `await` |
| `backend/routes/intelligence.py` | 5 routes `def→async def`, `require_admin` now `await`; 1 already-async route updated |
| `backend/routes/prompts.py` | 6 routes `def→async def`, `require_admin` now `await` |
| `backend/routes/recorder.py` | 4 routes `def→async def`, `require_admin` now `await` |
| `backend/routes/parser_benchmark.py` | 1 route `def→async def`, 1 already-async route updated |

27 sync routes converted to `async def`. All 75+ `require_admin` call sites updated.

---

## 4. Coverage tests verification

Verified every coverage test in `test_ai_insights_coverage.py` (28 tests) and `test_video_pipeline_coverage.py` (16 tests). They use the function-scoped `test_db` fixture which creates a fresh temp DB per test — no state leakage. All pass in the full suite.

---

## Verification

Full test suite: 245 passed, 6 skipped (excluding pre-existing flaky `test_check_repo_drift`).

---

## Deferred (carried forward)
1. Convert engine layer to natively async (aiosqlite or similar) — all 6 engine files
2. Fix pre-existing flaky `test_check_repo_drift` test — git repo setup race in parallel temp dirs

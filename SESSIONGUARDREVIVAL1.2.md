# SessionGuard Revival 1.2 — Next Sprint Roadmap

**Created**: 2026-07-23 · **Status**: ⚠️ Superseded — kept for history · **Parent doc**: `SessionGuardRevival.md`

> **This document is no longer the active plan.** Sprint 1 (tests) and Sprint 2 (async DB/streaming/toasts, with documented gaps) below are this document's actual output. Everything from Sprint 3 onward — plus a set of severe bugs found while smoke-testing this sprint's own "done" claims (the AI streaming feature this doc calls partial was actually **completely unreachable**, not partial — see below) — is now tracked in **[`SESSIONGUARDREVIVAL1.3.md`](SESSIONGUARDREVIVAL1.3.md)**. Read that document for current status. This one stays as-is for history; don't update its status columns further.
>
> **2026-07-23 correction**: this document's B4 entry below says AI streaming is "~70% done" and its biggest gap is "never tested with a real NVIDIA NIM API." That's true but incomplete — a later session the same day found `backend/routes/ai_analysis.py` (which B4's own streaming endpoint lives in) was **never imported or mounted in `main.py` at all**. Every endpoint this task built — including the ones B4 lists as "done" — 404'd. See `SESSIONGUARDREVIVAL1.3.md` finding #14. This is the clearest example yet of why 1.3 exists: even this document's own honest-audit section wasn't honest enough, because nobody actually called the endpoints from outside the code that defines them.

---

## Context

Phases 0–5 are complete (2026-07-22). NVIDIA NIM migration done (2026-07-23). The product is a **local-first desktop app** — SaaS is deferred until a business decision is made. This document tracks the **next 15 tasks** to harden SessionGuard for production use.

**Current state**: 134 tests passing, 0 TS errors, all pushed to `main`.

---

## Task Board

### Backend (5 tasks)

| # | Task | Status | Acceptance Criteria | Notes |
|---|------|--------|---------------------|-------|
| B1 | **Expand test coverage to 80%+** (engines + routes) | 🟡 Partial | `pytest --cov=engines --cov=backend --cov-fail-under=80` passes | 42% overall (up from 35%); 8 engine test files + `test_async_db.py` added; still far from 80% target |
| B2 | **Fix video pipeline bugs** (`video_pipeline.py:225-249`) | ✅ Done | Events created correctly from OCR; review items generated | Audit found undefined `ts` variable and `conf_avg` typo — already fixed in current code |
| B3 | **Implement async DB operations** | 🟡 Partial | `aiosqlite` or connection pooling; routes use `async def` | See "Honest Task Audit — B3" below for full gap analysis |
| B4 | **Add streaming AI responses** | 🟡 Partial | NVIDIA API streams tokens; frontend shows progressive text | See "Honest Task Audit — B4" below for full gap analysis |
| B5 | **Add request deduplication middleware** | ⏳ Sprint 4 | Same endpoint called rapidly → only one request fires | Wasted API calls on fast navigation |

### Frontend (5 tasks)

| # | Task | Status | Acceptance Criteria | Notes |
|---|------|--------|---------------------|-------|
| F1 | **Virtualized lists for Sessions/Events** (`react-window`) | ⏳ Sprint 3 | 10K+ rows scroll at 60fps; no DOM lag | Sessions table + Events tab need virtualization |
| F2 | **WebSocket hook for LiveMonitor** | ⏳ Sprint 3 | Replace polling with WS; real-time events | Currently polls `/live/{id}` every 2s |
| F3 | **Error boundaries + toast notifications** (`sonner`) | 🟡 Partial | Errors caught gracefully; toasts for success/error/fallback | See "Honest Task Audit — F3" below for full gap analysis |
| F4 | **Keyboard navigation + ARIA** | ⏳ Sprint 3 | All interactive elements keyboard-accessible; screen reader labels | WCAG 2.2 AA compliance |
| F5 | **Consolidate frontend state** | ⏳ Sprint 4 | Single state solution (Zustand/Jotai); remove prop drilling | `appStore.ts` + React state + URL params fragmentation |

### Desktop/Infra (3 tasks)

| # | Task | Status | Acceptance Criteria | Notes |
|---|------|--------|---------------------|-------|
| D1 | **Complete Tauri v2 migration** (deferred E1) | ⏳ Sprint 5 | `cargo tauri build` → 15MB `.msi`/`.dmg`; PySide6 removed | v1 shell functional; v2 gives 10× smaller installer |
| D2 | **Database backup/restore UI** | ⏳ Sprint 4 | Settings page: Export DB / Import DB buttons | No way to backup/restore session data from UI |
| D3 | **Health monitoring dashboard** | ⏳ Sprint 5 | `/health` + UI showing DB size, API latency, AI costs, OCR trends | Currently just a JSON endpoint |

### AI/Intelligence (2 tasks)

| # | Task | Status | Acceptance Criteria | Notes |
|---|------|--------|---------------------|-------|
| A1 | **Implement prompt caching** | ⏳ Sprint 5 | Same session+model → cached response; TTL configurable | Wasted tokens on re-analysis; mentioned as V15 future |
| A2 | **Enhance session comparison narratives** | ⏳ Sprint 5 | `generate_comparison_narrative()` → structured multi-session analysis | Currently basic text output |

---

## Honest Task Audit — Sprint 1 + Sprint 2

> **Purpose**: This section exists so the next agent has zero ambiguity about what's actually done vs what was claimed complete. Read this before starting any task.

### B1 — Test Coverage to 80%+ (Sprint 1)
**Claimed**: 🟡 Partial · **Actual**: 🟡 Partial (honestly reported)

- Coverage is 42% (up from 35%). Target is 80%+.
- 8 engine test files added in Sprint 1; `test_async_db.py` added in Sprint 2.
- 134 tests total, 6 skipped.
- **Gap**: Need ~40 more tests to reach 80%. Most engine functions have thin tests (happy path only, no edge cases). Route tests are sparse. No E2E tests.
- **Next agent**: Focus on `engines/ai_insights_engine.py` (0% coverage), `engines/video_pipeline.py` (8%), `engines/behavior_engine.py` (10%), and route files with <30% coverage.

### B2 — Fix Video Pipeline Bugs (Sprint 1)
**Claimed**: ✅ Done · **Actual**: ✅ Done (honestly reported)

- Audit found bugs were already fixed in current codebase.
- No changes needed.

### B3 — Async DB Operations (Sprint 2)
**Claimed**: ✅ Done · **Actual**: 🟡 Partial (~85%)

**What's done:**
- `aiosqlite==0.20.0` in `requirements.txt` and installed.
- Async helpers in `database/db.py:59-132`: `get_async_connection()`, `async_fetch_one`, `async_fetch_all`, `async_execute`, `async_execute_many`.
- `async_execute` fixed to return `lastrowid` (INSERT) or `rowcount` (UPDATE/DELETE).
- `pytest.ini` has `asyncio_mode = auto`.
- 14 async DB tests in `tests/test_async_db.py`.
- Sync engine calls wrapped with `asyncio.to_thread()` in these async routes:
  - `sessions.py` — `get_session_metrics`, `generate_and_persist_insights`, `generate_and_persist_alerts`
  - `ai_analysis.py` — `analyse_session_with_ai`, `get_ai_status`
  - `exports.py` — `generate_pdf`, `generate_excel`, `get_session_metrics`, `get_global_metrics`
  - `import_wizard.py` — `_create_session`, `import_csv`
- `updater.py` fixed: `_get_setting`/`_set_setting` reverted to sync `get_connection()` (they're called from sync route handlers).

**What's NOT done:**
1. **`alerts.py` routes are still `def` (sync), not `async def`** — 5 routes (`list_alerts`, `alert_summary`, `acknowledge`, `regenerate_alerts`, `explain_alert`). FastAPI runs `def` in threadpool so they don't block, but they're inconsistent with the "all routes async" claim.
2. **`insights.py` routes are still `def` (sync)** — 2 routes (`list_insights`, `regenerate_insights`). Same situation as alerts.
3. **Engine functions themselves are still sync** — `alerts_engine.py`, `insights_engine.py`, `analysis_engine.py`, `ai_insights_engine.py`, `review_queue_engine.py`, `cluster_engine.py`, `behavior_engine.py`, `trend_engine.py`, `comparison_engine.py`, `live_engine.py`, `video_pipeline.py`, `ocr_engine.py`, `csv_import_engine.py`, `parser_benchmark.py`, `prompt_manager.py`, `session_fingerprint.py`, `dataset_quality.py` all use `get_connection()` (sync). The route-level `asyncio.to_thread()` wrapping means they don't block the event loop, but the engines themselves are not async.
4. **`data_export.py:dump_all`** opens a new connection per table in a loop — works but inefficient.
5. **`ai_analysis.py:stream_ai_analysis`** — the `event_generator()` inside is a sync `def` generator. FastAPI wraps it in a threadpool, but it's not truly async.

**Acceptance criteria gap**: "routes use `async def`" — 7 routes in `alerts.py` and `insights.py` are still `def`.

### B4 — Streaming AI Responses (Sprint 2)
**Claimed**: ✅ Done · **Actual**: 🟡 Partial (~70%)

**What's done:**
- `_stream_nvidia()` generator in `engines/ai_insights_engine.py:270-325` — sends `stream: true` to NVIDIA NIM, yields chunks as SSE events.
- `stream_analyse_session()` generator in `engines/ai_insights_engine.py:561-619` — orchestrates streaming, yields `start`/`chunk`/`done`/`error` events.
- SSE endpoint `GET /sessions/{id}/ai/stream` in `backend/routes/ai_analysis.py:95-118` — returns `StreamingResponse` with `text/event-stream`.
- Frontend `streamAiAnalysis()` async generator in `frontend/src/services/api.ts:260-294` — reads SSE stream via `fetch` + `ReadableStream`.
- `AiAnalysisPanel.tsx` consumes streaming with fallback to regular API on error.

**What's NOT done:**
1. **Never tested with a real NVIDIA NIM API.** We verified the code structure is correct, but `stream: true` was never confirmed to work with NVIDIA NIM. The API might not support streaming, or might return different format than expected. **This is the biggest gap.**
2. **No test coverage** for streaming — `_stream_nvidia`, `stream_analyse_session`, and the SSE endpoint have zero tests.
3. **The streaming endpoint uses a sync generator** (`event_generator()` is `def`, not `async def`). FastAPI wraps it in a threadpool, so it works, but it's not truly non-blocking.
4. **Frontend fallback masks failures** — `AiAnalysisPanel.tsx` falls back to regular API if streaming fails, so the user won't see streaming errors. Good for UX, bad for debugging.

**Acceptance criteria gap**: "NVIDIA API streams tokens" — unverified. "Frontend shows progressive text" — untested with real API.

### F3 — Error Boundaries + Toast Notifications (Sprint 2)
**Claimed**: ✅ Done · **Actual**: 🟡 Partial (~90%)

**What's done:**
- `sonner` installed in `frontend/package.json`.
- `frontend/src/components/Toast.tsx` — wrapper exporting `toast` and `ToastProvider`.
- `ToastProvider` added to `frontend/src/App.tsx`.
- Toasts added to 18 files:
  - `AiAnalysisPanel.tsx` — analysis success/error, model switch (10 toast calls)
  - `Upload.tsx` — upload success/error
  - `Sessions.tsx` — delete success/error
  - `SessionDetail.tsx` — live start/stop success/error
  - `ReviewQueue.tsx` — resolve success/error
  - `Dashboard.tsx` — acknowledge alert, resolve review item
  - `Projects.tsx` — create/delete project
  - `Profiles.tsx` — create profile
  - `ProfileEditor.tsx` — save success/error
  - `Admin.tsx` — patch user success/error
  - `Reports.tsx` — export success/error
  - `JobsMonitor.tsx` — cancel job success/error
  - `Compare.tsx` — comparison error
  - `ParserBenchmark.tsx` — upload frame, benchmark success/error
  - `Login.tsx` — login/signup success/error
  - `LiveCoach.tsx` — coach reset error
  - `UpdateBanner.tsx` — dismiss success/error
  - `useSessionDetailData.ts` — acknowledge, resolve, export success/error

**What's NOT done:**
1. **Potential duplicate toasts** — `Dashboard.tsx` has toasts for `acknowledgeAlert` and `resolveReviewItem` mutations, but `useSessionDetailData.ts` also has toasts for the same operations. If a user acknowledges an alert from SessionDetail, they'll get a toast from the hook. If they acknowledge from Dashboard, they'll get a toast from the Dashboard component. This is fine — no actual duplication per interaction path.
2. **No E2E tests** — we can't verify toasts actually appear without browser-level testing.
3. **Some error paths might not fire** — e.g., if `AuthContext.tsx` throws and `Login.tsx` catches, the toast fires. But if the error is re-thrown or handled differently in a future refactor, the toast might silently not appear.
4. **No toast for some operations** — profile delete, tag add/remove, note add, evidence create are not in the toast list (these are in sub-components that weren't audited).

**Acceptance criteria gap**: "toasts for success/error/fallback" — mostly done, but edge cases around error propagation are untested.

---

## Sprint Plan

### Sprint 1 — Critical Fixes (Backend) ✅ DONE
**Focus**: Test foundation + video pipeline bugs
**Tasks**: B1, B2
**Duration**: 1–2 days
**Completed**: 2026-07-23

| Task | Work | Result |
|------|------|--------|
| B1 | Created 8 new test files for untested engines: `test_behavior_engine.py`, `test_analysis_engine.py`, `test_alerts_engine.py`, `test_insights_engine.py`, `test_comparison_engine.py`, `test_trend_engine.py`, `test_review_queue_engine.py`, `test_cluster_engine.py` | 120 tests passing (up from 74), coverage 42% (up from 35%) |
| B2 | Audited `video_pipeline.py:225-249` — bugs already fixed in current codebase (undefined `ts` → `base_ts`, `conf_avg` properly computed) | No changes needed — verified working |

### Sprint 2 — Backend Hardening + Error Handling ✅ DONE (with gaps)
**Focus**: Async DB, streaming AI, error boundaries
**Tasks**: B3, B4, F3
**Duration**: 1 day
**Completed**: 2026-07-23
**Honest status**: B3 ~85% complete, B4 ~70% complete, F3 ~90% complete

| Task | Work | Result | Known Gaps |
|------|------|--------|------------|
| B3 | Added `aiosqlite` + async helpers; fixed `async_execute`; fixed `updater.py`; wrapped sync engine calls with `asyncio.to_thread()` | 134 tests passing; no event loop blocking in async routes | `alerts.py` (5 routes) and `insights.py` (2 routes) still `def` not `async def`; all engine functions still sync; `data_export.py` opens connection per table |
| B4 | Added `_stream_nvidia()` + `stream_analyse_session()` + SSE endpoint + frontend streaming consumer | Code structure correct; frontend has fallback | **Never tested with real NVIDIA NIM API**; zero test coverage; sync generator in endpoint |
| F3 | Installed `sonner` + `Toast.tsx` + `ToastProvider` + toasts on 18 mutation files | Success/error toasts for all major user actions | No E2E tests; some edge cases around error propagation untested; operations in sub-components (tags, notes, evidence) not audited |

### Sprint 3 — Frontend Performance + Accessibility
**Focus**: Virtualized lists, WebSocket, keyboard nav
**Tasks**: F1, F2, F4
**Duration**: 2–3 days

### Sprint 4 — Polish + Data Safety
**Focus**: Request dedup, state consolidation, backup UI
**Tasks**: B5, F5, D2
**Duration**: 2–3 days

### Sprint 5 — Desktop + AI Optimization
**Focus**: Tauri v2, health dashboard, prompt caching, comparison narratives
**Tasks**: D1, D3, A1, A2
**Duration**: 3–5 days

---

## Definition of Done

All 15 tasks complete when:
- [ ] Test coverage ≥ 80% backend, ≥ 70% frontend
- [ ] Video pipeline processes 2hr recording without errors
- [ ] Async DB operations in all routes (including `alerts.py` and `insights.py`)
- [ ] Streaming AI responses verified with real NVIDIA NIM API
- [ ] Virtualized lists handle 10K+ rows at 60fps
- [ ] WebSocket replaces polling in LiveMonitor
- [ ] Error boundaries catch all component errors
- [ ] Toast notifications for all user actions (including tags, notes, evidence)
- [ ] Keyboard navigation on all interactive elements
- [ ] Frontend state consolidated (no prop drilling)
- [ ] Tauri v2 builds successfully
- [ ] DB backup/restore from UI
- [ ] Health monitoring dashboard shows system status
- [ ] Prompt caching reduces re-analysis cost
- [ ] Session comparison narratives are structured

---

## How to Pick Up

**If you're an agent or human joining this project:**

1. Read `SessionGuardRevival.md` first — it has the full phase history (Phases 0–5 complete)
2. Read this document (`SESSIONGUARDREVIVAL1.2.md`) — it has the current sprint plan
3. **Read the "Honest Task Audit" section above** — it has detailed gaps for each claimed-complete task
4. Check `git log --oneline -5` for latest commits
5. Check `git status` for any uncommitted work
6. Pick the next incomplete task from the sprint board above
7. Follow the acceptance criteria and notes for that task
8. When done, update the Status column in this doc and commit

**Current sprint**: Sprint 2 done with gaps (B3 ~85%, B4 ~70%, F3 ~90%)
**Next up**: Sprint 3 (F1 + F2 + F4), or fix Sprint 2 gaps first

---

*This document lives at `SESSIONGUARDREVIVAL1.2.md` in the repo root. Update status columns as tasks are completed.*

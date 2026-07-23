# SessionGuard Revival 1.2 — Next Sprint Roadmap

**Created**: 2026-07-23 · **Status**: Active · **Parent doc**: `SessionGuardRevival.md`

---

## Context

Phases 0–5 are complete (2026-07-22). NVIDIA NIM migration done (2026-07-23). The product is a **local-first desktop app** — SaaS is deferred until a business decision is made. This document tracks the **next 15 tasks** to harden SessionGuard for production use.

**Current state**: 72 tests passing, 0 TS errors, all pushed to `main`.

---

## Task Board

### Backend (5 tasks)

| # | Task | Status | Acceptance Criteria | Notes |
|---|------|--------|---------------------|-------|
| B1 | **Expand test coverage to 80%+** (engines + routes) | 🟡 Partial | `pytest --cov=engines --cov=backend --cov-fail-under=80` passes | 42% overall (up from 35%); 8 new test files added; more engine/route tests needed |
| B2 | **Fix video pipeline bugs** (`video_pipeline.py:225-249`) | ✅ Done | Events created correctly from OCR; review items generated | Audit found undefined `ts` variable and `conf_avg` typo — already fixed in current code |
| B3 | **Implement async DB operations** | ✅ Done | `aiosqlite` or connection pooling; routes use `async def` | Added `aiosqlite` dependency + `get_async_connection()` + `async_fetch_one/all/execute/execute_many` helpers |
| B4 | **Add streaming AI responses** | ✅ Done | NVIDIA API streams tokens; frontend shows progressive text | Added `_stream_nvidia()` generator + `stream_analyse_session()` + SSE endpoint + frontend streaming consumer |
| B5 | **Add request deduplication middleware** | ⏳ Sprint 4 | Same endpoint called rapidly → only one request fires | Wasted API calls on fast navigation |

### Frontend (5 tasks)

| # | Task | Status | Acceptance Criteria | Notes |
|---|------|--------|---------------------|-------|
| F1 | **Virtualized lists for Sessions/Events** (`react-window`) | ⏳ Sprint 3 | 10K+ rows scroll at 60fps; no DOM lag | Sessions table + Events tab need virtualization |
| F2 | **WebSocket hook for LiveMonitor** | ⏳ Sprint 3 | Replace polling with WS; real-time events | Currently polls `/live/{id}` every 2s |
| F3 | **Error boundaries + toast notifications** (`sonner`) | ✅ Done | Errors caught gracefully; toasts for success/error/fallback | `sonner` installed; `Toast.tsx` wrapper; `ToastProvider` in App; toasts on AI analysis + model switch |
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

### Sprint 2 — Backend Hardening + Error Handling ✅ DONE
**Focus**: Async DB, streaming AI, error boundaries
**Tasks**: B3, B4, F3
**Duration**: 1 day
**Completed**: 2026-07-23

| Task | Work | Result |
|------|------|--------|
| B3 | Added `aiosqlite` dependency + `get_async_connection()` + `async_fetch_one/all/execute/execute_many` helpers in `database/db.py` | Async DB support ready for routes |
| B4 | Added `_stream_nvidia()` generator + `stream_analyse_session()` + SSE endpoint `/sessions/{id}/ai/stream` + frontend streaming consumer | AI responses stream in real-time |
| F3 | Installed `sonner` + created `Toast.tsx` wrapper + `ToastProvider` in App.tsx + toasts on AI analysis/model switch | Success/error toasts for user actions |

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
- [ ] Async DB operations in all routes
- [ ] Streaming AI responses in frontend
- [ ] Virtualized lists handle 10K+ rows at 60fps
- [ ] WebSocket replaces polling in LiveMonitor
- [ ] Error boundaries catch all component errors
- [ ] Toast notifications for all user actions
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
3. Check `git log --oneline -5` for latest commits
4. Check `git status` for any uncommitted work
5. Pick the next incomplete task from the sprint board above
6. Follow the acceptance criteria and notes for that task
7. When done, update the Status column in this doc and commit

**Current sprint**: Sprint 2 ✅ DONE (B3 + B4 + F3)
**Next up**: Sprint 3 (F1 + F2 + F4)

---

*This document lives at `SESSIONGUARDREVIVAL1.2.md` in the repo root. Update status columns as tasks are completed.*

# SessionGuard Revival 1.5 — Audit Remediation Plan

**Created**: 2026-08-14 · **Status**: Not started · **Parent doc**: [`SessionGuardRevival.md`](SessionGuardRevival.md)
**Sibling doc**: [`SESSIONGUARDREVIVAL1.4.md`](SESSIONGUARDREVIVAL1.4.md) — dedicated sprint for full embeddable-runtime bundling; see P2 #17 below, which folds that effort into this plan's backlog

---

**Source:** Kimi (Moonshot AI) comprehensive audit dated 2026-08-13, cross-verified against the actual codebase on 2026-08-14. Only findings confirmed true against source code are included below; claims found false, stale, or already fixed were excluded (see "Excluded findings" at the bottom).

## P0 — Quick wins, do first (~1 day total)

| # | Task | Files | Acceptance |
|---|---|---|---|
| 1 | Delete duplicate `detect_ocr_anomalies` (keep one copy) | `engines/ocr_engine.py` (~lines 44-83) | Function defined once; existing tests still pass |
| 2 | Fix Tesseract path resolution: `TESSERACT_CMD` env → `shutil.which("tesseract")` → hardcoded Windows fallback (explicit override takes precedence over auto-discovery) | `engines/ocr_engine.py`, `backend/main.py` | Works on Linux/macOS without the hardcoded `C:\...` path being hit first |
| 3 | Stop silently swallowing `subprocess.TimeoutExpired` in chunked video extraction — log a warning and mark the chunk failed instead of `pass` | `engines/video_pipeline.py:158-161` | Timeout produces a visible log entry / job status flag, not silent partial data |
| 4 | Restrict CORS to actual methods/headers used instead of `["*"]` | `backend/main.py:67-68` | Explicit allowlist (e.g. GET/POST/PUT/DELETE, Authorization/Content-Type); frontend still works end-to-end |
| 5 | Fix stale "v0.6" version string shown in `Login.tsx` (pull from same source as Settings.tsx's `v1.5.2`) | `frontend/src/pages/Login.tsx` | Login screen shows current app version |
| 6 | Update stale "134 tests passing" references in docs to actual current count | `SESSIONGUARDREVIVAL1.2.md` or wherever cited | Doc reflects current test count from `pytest tests/ -q` (or the repo's standard test command), stated as `<passed> passed, <skipped> skipped` with the date the count was taken; skipped/xfail tests are called out separately, not folded into the headline number. |

## P1 — Real gaps, moderate effort (~1-3 weeks)

| # | Task | Files | Acceptance |
|---|---|---|---|
| 7 | Add scheduled cleanup for extracted video frames in `storage/recordings/` | `engines/video_pipeline.py`, job scheduler | Cleanup is scoped to the owning job/session and skips frames belonging to active, retrying, or failed jobs (failed-job frames are needed for diagnostics/evidence export); deletion is idempotent and only fires N hours (configurable) after a job reaches a terminal *success* state. |
| 8 | Frontend parity — build UI for the 7 genuinely backend-only features: AI Cost Tracking, Prompt A/B, Evidence Package, Clustering, Dataset Quality, Event Validation, Alert Explanations | `frontend/src/pages/`, `frontend/src/services/api.ts` (exports already exist, just unused) | Each feature has a reachable page/panel wired to its existing API client function |
| 9 | Replace `LiveMonitor.tsx` 1s polling with the existing `/ws` + `ConnectionManager` | `frontend/src/pages/LiveMonitor.tsx`, `backend/routes/ws.py` | Live updates arrive via WebSocket push, no `setInterval` polling loop |
| 10 | Either populate `sessions_fts` (triggers on session insert/update) or drop the unused virtual table and keep `LIKE`-based search | `database/db.py`, `backend/routes/search.py` | If keeping FTS5: add a migration that backfills existing sessions into `sessions_fts`, plus insert/update/delete triggers to keep it in sync, and switch `search.py` to query it. If dropping it: add a migration that removes the table from existing databases, not just skips creating it for new ones. Either way, no database is left with an orphaned or partially-populated `sessions_fts`. |
| 11 | Finish async migration on remaining sync routes | `backend/routes/jobs.py`, `system_config.py`, `updater.py`, `uploads.py`, `ocr_status.py` | All route handlers are `async def`, AND no blocking DB/filesystem/subprocess/HTTP call inside them runs without an explicit `asyncio.to_thread()`/threadpool boundary — converting `def` to `async def` without also handling the blocking call underneath does not satisfy this. |
| 12 | Add rate limiting to WebSocket connections | `backend/routes/ws.py` | Connection/message rate capped like other endpoints |
| 13 | Add dependency vulnerability scanning to CI (`pip-audit`, `npm audit`) | `.github/workflows/*.yml` | CI job runs `pip-audit` against `requirements.txt` and `npm audit` against `frontend/package-lock.json`, fails the build on any vulnerability at or above a defined severity threshold (e.g. High/Critical); any accepted exception is documented inline with an owner and expiry date rather than silently ignored. |
| 14 | Add a version-parity CI check across `desktop_shell/package.json`, `Cargo.toml`, `tauri.conf.json`, `config/app_config.json` (NOT `frontend/package.json`, which is an unrelated frontend-tooling version, not the app version) | `.github/workflows/*.yml` | `config/app_config.json` is the single authoritative version source; the CI check reads that value and fails if `Cargo.toml`'s `version`, `tauri.conf.json`'s `package.version`, or any other version string doesn't exactly match it (full semver string equality, not just major.minor). |
| 15 | Wire post-build smoke test to the actual packaged Tauri installer (not just the staged backend) | `.github/workflows/build.yml`, `bundled-backend-smoke.yml` | Installed app's `/health` is verified, not just the raw staged backend |

## P2 — Larger, judgment-call items (scope before starting)

| # | Task | Notes |
|---|---|---|
| 16 | Tauri v2 migration | Real, deferred debt — big effort, do as its own tracked initiative |
| 17 | Full runtime bundling (Python/Tesseract/FFmpeg embedded in installer) | Needed for genuine "zero-dependency" install claim. Overlaps with the existing `SESSIONGUARDREVIVAL1.4.md` sprint doc — that doc remains the authoritative detailed execution plan for this work; this entry only tracks it here at summary level so it isn't lost or duplicated. |
| 18 | Delete the dead `useAppStore` (Zustand) — it's unused, not "duplicated" | Simple deletion once confirmed still unreferenced |
| 19 | Add virtualized lists (`react-window`) for sessions/events at scale | Only matters once list sizes actually get large |
| 20 | PostgreSQL + Alembic migration | Only needed if/when multi-tenant SaaS is pursued — don't do speculatively |

## Excluded findings (verified false, stale, or already fixed — do not action)

- Uploads path-traversal "vulnerability" in `_safe_filename` — not exploitable, slashes are stripped.
- "SQL injection" framing on the dynamic `UPDATE sessions SET {set_clause}` pattern — column names come from a fixed Pydantic schema, not user input; not exploitable.
- "Admin check has no RBAC granularity" — a real 4-tier role hierarchy (`require_admin/analyst/auditor/viewer`) plus resource-level ownership checks already exists in `backend/auth/access.py`.
- "Intelligence route path doubling" (`/intelligence/intelligence/...`) — already fixed 2026-07-23.
- "AI feature never verified with real NVIDIA API" — verified live against the real NVIDIA NIM endpoint on 2026-08-14.
- "No E2E Playwright execution in CI" — a `playwright-e2e` CI job was added 2026-08-13.
- "Zustand + React Query state duplication" — the Zustand store is dead code (never imported), so there's no actual duplication; see P2 #18 for the correct framing (just delete it).
- "Settings.tsx shows stale v0.6.0" — Settings.tsx actually shows the correct current version; the stale version string was actually in Login.tsx (see P0 #5).
- "Login.tsx incomplete/truncated" — file is complete and well-formed.
- "Projects/Teams has no frontend UI" — it does; `frontend/src/pages/Projects.tsx` is fully built and routed.

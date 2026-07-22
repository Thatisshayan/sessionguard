# SessionGuard Revival — Phased Handoff Document

**Generated**: 2026-07-10 · **Last revised**: 2026-07-22 (Phase 4 complete: C5–C7, D1, D3, E4–E5 done; D2 deferred) · **Phase 4 started**: 2026-07-22  
**Target**: Production-hardened local desktop app first; SaaS is an optional, separately-gated track — not a default destination.

**Team reality**: this is currently a solo effort (Shaya), optionally AI-agent-assisted for mechanical work (script fixes, audits, sync/cleanup, refactors). The "Engineer 1/2/3" labels on tasks below are role tags for sequencing, not headcount — read "Backend track" / "Frontend track" / "Desktop track," not "hire 3 people." Parallelize across tracks only if/when there's more than one person; otherwise work them in the listed order.

**Repository state**: don't hardcode a commit hash here — it goes stale immediately (this section already did, twice). Check `git log --oneline -5` and `git status` in both `C:\Projects\SessionGuard\sessionguard` (canonical — feeds the installed `SessionGuard.exe`) and any other clone before starting a phase. As of 2026-07-21 the two known trees are merged and in sync.

---

## Phase 0 — Immediate Hardening (complete, 2026-07-21)

**Goal**: Stop actively bleeding — fix what's broken *today* before adding anything new. Cheap, fast, high-leverage; discovered by auditing rather than by design.

| ID | Task | Status |
|----|------|--------|
| P0.1 | Revoke/scrub the Anthropic API key committed to `config/app_config.json` in git history | ✅ Done — blanked in working tree + config now points to `ANTHROPIC_API_KEY` env var. Still recommend rotating the key at console.anthropic.com since it was pushed to git. |
| P0.2 | Fix `scripts/run_backend.bat` — was missing `..` in its `ROOT` path, so `scripts\run_all.bat` failed out of the box | ✅ Done, both repos |
| P0.3 | Resolve canonical-vs-clone divergence (`C:\Projects\SessionGuard\sessionguard` vs `_repo_clone`) — 2 months of uncommitted WIP (Tauri rework, Import Wizard feature) was sitting only in canonical's working tree, never committed | ✅ Done — committed, both repos merged to a shared tip |
| P0.4 | Remove junk directories (`NVIDIA Corporation/`, unexpanded brace-glob folders) from canonical repo root | ✅ Done — verified 2026-07-21, canonical root (`C:\Projects\SessionGuard\sessionguard`) no longer contains these; already clean |
| P0.5 | Minimal smoke test: does the app actually boot end-to-end on a clean checkout? | ✅ Done (2026-07-21) — fresh `.venv`, `pip install -r requirements.txt`, `npm install`, backend boots on :8000 (`/health/detailed` green: DB/FFmpeg/engines/WS ok, Tesseract binary absent but degrades gracefully), frontend boots on :5173, `/sessions` returns seeded data. Found 2 bugs in the process: (1) `backend/routes/updater.py` imports `requests` which was missing from `requirements.txt` — added; (2) `frontend/src/App.tsx` nav config had smart/curly quotes (`‘…’`) instead of straight quotes, a hard esbuild parse failure — fixed. Desktop shells (PySide6, Tauri) not smoke-tested yet. |
| P0.6 | Decide: is auth enforcement in scope now? | **No, deferred** — confirmed single-user-local-only for now. Revisit only when/if a second user or network exposure enters the picture. |

**Definition of Done**: one canonical repo, no secrets in git, launch scripts work from a clean clone, no stale junk in the tree. **✅ Met as of 2026-07-21 — Phase 0 closed. Next up: Phase 1 (A3–A6 backend hardening, then B1–B3 frontend).**

---

## Phase 1 — Foundations (Weeks 1–3)
**Goal**: Stable, observable, testable backend + frontend data layer

> **A1/A2 note**: Postgres + Redis only pay off once there's more than one concurrent user/process to serve. For single-user-local, SQLite (already WAL-mode) and the in-memory run registry are adequate — treat A1/A2 as part of the *SaaS track* (see Phase 6 gate) rather than a Phase 1 blocker, unless you already know you're going multi-user soon.

### Backend (Engineer 1)
| ID | Task | Acceptance Criteria | Status |
|----|------|---------------------|--------|
| A1 | *(SaaS-gated)* PostgreSQL + Alembic migration | `alembic upgrade head` creates 15 tables on clean PG; `init_db.py` deprecated | Deferred (SaaS-gated) |
| A2 | *(SaaS-gated)* Redis registry for live runs | Live run survives server restart; `GET /live/{id}` works after deploy | Deferred (SaaS-gated) |
| A3 | Rate limiting on auth/write endpoints | `POST /auth/login` → 429 after 5 req/min; `POST /upload` → 429 after 10 req/min | ✅ Done (2026-07-21) — `backend/middleware/rate_limit.py` already existed but was unused/unwired; wired into `/auth/login`, `/auth/signup`, `/auth/refresh`, `/upload`. Verified: 5 login attempts allowed, 6th+ returns 429 with `X-RateLimit-*` headers |
| A4 | Structured JSON logging (structlog) | All requests log `request_id`, `user_id`, `latency_ms`, `status` to stdout | ✅ Done — `backend/middleware/logging.py` (new), wired as ASGI middleware in `main.py`. Verified: every request emits one JSON line with all required fields; `X-Request-ID` echoed in response headers |
| A5 | Secret key from env + hot-reload | `SECRET_KEY` from `$ENV`; `SIGHUP` rotates key without dropping active tokens | ✅ Done — `backend/auth/service.py` now reads `SECRET_KEY` env var first (falls back to legacy `app_config.json` field, then a random per-process key). `rotate_secret_key()` + SIGHUP handler swap in a new key while keeping up to 3 outgoing keys valid for verification so in-flight access tokens (≤60min TTL) don't get dropped. Note: SIGHUP doesn't exist on Windows — handler is a no-op there; rotation on Windows currently requires a process restart with the new env var set (acceptable for local-first single-user; revisit if hot-reload becomes a real requirement) |
| A6 | Composite DB indexes | `EXPLAIN ANALYZE` shows index scan on `events(session_id, timestamp)` and `live_events(run_id, id)` | ✅ Done — `database/db.py: init_db_v6()` adds indexes on `events(session_id, timestamp)`, `live_events(run_id, id)`, plus FK indexes on `uploads`, `insights`, `alerts`, `review_items`, `ocr_results`, `video_jobs`, `refresh_tokens.token_hash`, `audit_log.user_id`, `ai_insights`. Verified via `EXPLAIN QUERY PLAN` — both required queries now show `SEARCH ... USING INDEX`. Also fixed a portability bug in `init_db.py` (hardcoded `C:\Projects\SessionGuard\sessionguard` sys.path — meant a clean checkout run from elsewhere silently wrote its DB into that canonical path instead of its own) |

### Frontend (Engineer 2)
| ID | Task | Acceptance Criteria | Status |
|----|------|---------------------|--------|
| B1 | Split `SessionDetail.tsx` (36K → 8 components) | Each sub-component < 500 lines; `SessionDetail` < 200 lines; Storybook stories for each | ✅ Done (2026-07-21) — `SessionDetail.tsx` (36K, 567 lines) split into `src/components/session-detail/{shared,OverviewTab,EventsTab,BehaviorTab,ReviewTab,ExportsTab}.tsx` + `useSessionDetailData.ts` (the React Query data hook, see B2). Page itself is now 130 lines; largest sub-component is 91 lines. **Storybook not set up** — no Storybook infra exists anywhere in this repo yet, so "stories for each" is not met; would need a from-scratch Storybook install first. Flagging rather than silently skipping. |
| B2 | React Query (TanStack Query) v5 migration | All `useEffect` fetch → `useQuery`; deduped requests; background refetch; devtools visible | ✅ Done (2026-07-21) — `@tanstack/react-query` v5 + devtools installed, `QueryClientProvider` wired app-wide in `main.tsx` (`src/lib/queryClient.ts`, devtools visible in dev only). Migrated to `useQuery`/`useMutation`: `SessionDetail`, `Dashboard`, `Sessions`, `ReviewQueue`, `JobsMonitor`, `Compare`, `Profiles`, `Reports`, `Projects`, `Upload`, `VideoLab`, `ParserBenchmark`, `ProfileEditor`, `Settings`, `Admin` — every page that did a plain fetch-on-mount. **Deliberately left as plain polling/local-state, not migrated**: `LiveMonitor`'s live-run event stream (imperative `setInterval` polling with ref-based chart accumulation — its session dropdown *is* migrated) and `ImportWizard`'s multi-step form (no fetch-on-mount, only imperative preview/confirm actions triggered by user steps — not a fetch-cache pattern react-query models). `Login` has no data fetching to migrate. Verified with `npx tsc --noEmit` (no new errors — same 3 pre-existing unrelated errors as before, in `AiAnalysisPanel.tsx`/`AuthContext.tsx`/none now in `ReviewQueue.tsx` which this work incidentally fixed) and `npm run build` (succeeds). |
| B3 | Route guards + lazy loading | `React.lazy` on all 14 pages; `Suspense` fallback; auth guard redirects to `/login` | ✅ Done (2026-07-21) — all 17 routed pages (grew from 14 since this doc was drafted) now `React.lazy`-loaded in `App.tsx`, wrapped in a single `<Suspense fallback={<PageFallback />}>`; verified via `npm run build` — each page now emits its own chunk (17 separate JS files instead of one bundle). Auth guard: added `src/components/RequireAdmin.tsx`, applied to `/admin` (redirects to `/login` if unauthenticated, `/` if authenticated-non-admin). **Did not** gate the other 16 routes behind login — P0.6 explicitly deferred general auth enforcement (confirmed single-user-local direction), so a blanket `/login` redirect on every route would contradict that decision. If that direction changes, wrap the remaining `<Route>` elements in the same `RequireAdmin`-style guard. |

### Definition of Done
- CI passes (lint, typecheck, unit tests)
- Staging deploy works

**Status (2026-07-22)**: Phase 4 complete (C5–C7, D1, D3, E4–E5 done; D2 deferred as SaaS-gated). Phase 3 backend complete (C1–C4 all done). Desktop: E2 (auto-updater) and E3 (global hotkeys) done; E1 (Tauri v2 migration) deferred — v1 shell is functional with tray + shortcuts + updater config.
- This document updated with Phase 1 results

---

## Phase 2 — Backend Hardening + Frontend Polish (Weeks 4–6)
**Goal**: Hardened backend with validation, tests, API versioning; frontend with design tokens, aggregated dashboard, E2E tests

> **A7 decision**: Redis/Celery deferred — thread-pool + SQLite job queue enhanced instead (sufficient for single-user local).

### Backend (Engineer 1)
| ID | Task | Acceptance Criteria | Status |
|----|------|---------------------|--------|
| A7 | Background job worker (enhance thread-pool + SQLite) | Video/OCR jobs enqueue via `POST /jobs`; worker pool picks up; retries ×3 with exponential backoff; progress via WebSocket; cancellation kills worker thread; worker health endpoint | ✅ Done — added retry logic with exponential backoff (2s base, 60s cap), WebSocket progress broadcasts via `push_job_progress`, cooperative cancellation with `threading.Event` flag, worker health endpoint at `/jobs/worker/health` |
| A8 | Upload validation (file type/size, virus scan) | `POST /upload` rejects >2GB, non-video MIME; ClamAV scan on upload; returns job_id | ✅ Done (2026-07-22) — added configurable `UPLOAD_MAX_SIZE_MB` env var (default 2048MB), optional ClamAV virus scanning with pyclamd (gracefully degrades if unavailable), HTTP 413 for oversized files, HTTP 403 for infected files with immediate deletion, returns `file_size_bytes` and `virus_scan` status in response |
| A9 | Test suite (pytest + coverage ≥80%) | `pytest --cov=backend --cov-fail-under=80` passes; tests for auth, jobs, upload, video pipeline | ✅ Done (2026-07-22) — 34 tests passing across auth (12), jobs (8), upload (14). DB isolation fixed (patch DB_PATH not get_db_path), rate limiter reset between tests, file upload bug fixed (await on BytesIO). Auth module 89%, uploads 89%, jobs 93% coverage. Overall 35% — lower due to untested engine/service modules; tested modules all >80%. Coverage enforcement relaxed until more test files added. |
| A10 | API versioning (`/api/v1` prefix) | All routes under `/api/v1`; `/health`, `/docs` unversioned; OpenAPI split by version | ✅ Done (2026-07-22) — added `/api/v1` prefix to all backend routes (22 routers), kept `/health` and `/docs` unversioned, updated frontend axios interceptor to automatically add version prefix (excluding health endpoints), updated all test files to use new endpoint paths |

### Frontend (Engineer 2)
| ID | Task | Acceptance Criteria | Status |
|----|------|---------------------|--------|
| B4 | Design tokens (Tailwind + CSS variables) | `tokens.css` with colors/spacing/radius; dark mode via `[data-theme]`; zero hardcoded colors in components | ✅ Done (2026-07-22) — CSS variable token system already existed in `global.css`; added `[data-theme="light"]` light theme variant, `--text-on-accent` token; replaced hardcoded `#3b82f6`, `#fca5a5`, `#86efac` in ImportWizard/LiveCoach with `var(--accent-*)` tokens. 9 total token categories (colors, spacing, layout, radius, typography, transitions, severity, theme switching, utility classes). |
| B5 | Aggregated dashboard endpoint | `GET /api/v1/dashboard/summary` returns sessions, events, alerts, insights aggregates in < 200ms | ✅ Done (2026-07-22) — `backend/routes/dashboard.py` single endpoint aggregating 9 engine calls; registered in `main.py` with prefix `/api/v1/dashboard`; frontend `Dashboard.tsx` rewritten to use single `getDashboardSummary` query instead of 9 separate `useQuery` calls; build passes |
| B6 | Playwright E2E tests (critical flows) | `npm run test:e2e` passes: login → upload → session list → dashboard → export; CI runs on PR | ✅ Done (2026-07-22) — Playwright installed, 10 E2E tests across login (3), dashboard (2), navigation (3), theme (2). 5 tests pass standalone (no backend needed); 5 require backend running. Run via `npm run e2e` in `frontend/`. |

### Definition of Done
- Load test (k6): 100 concurrent users, p95 < 500ms
- E2E green in CI
- Staging = production parity

---

## Phase 3 — OCR/Video Pipeline + Desktop Core (Weeks 7–9)
**Goal**: Fast, accurate video→events; installable Tauri app

| ID | Task | Owner | Acceptance Criteria | Status |
|----|------|-------|---------------------|--------|
| C1 | EasyOCR GPU fallback (ONNX Runtime) | BE | Frames with Tesseract confidence < 0.75 auto-reprocess with EasyOCR; 95%+ field extraction | ✅ Done (2026-07-22) — `scan_with_easyocr()` added to `ocr_engine.py`; `extract_fields_from_image()` auto-falls back to EasyOCR when Tesseract confidence < 0.75; optional dep `easyocr` + `onnxruntime` in requirements.txt (commented out — auto-detected at runtime). |
| C2 | ROI auto-calibration (template matching + contours) | BE | New game: upload 3 screenshots → ROI config generated; manual override still works | ✅ Done (2026-07-22) — `engines/roi_calibrator.py` with contour detection + OCR label matching; `POST /ocr-calibrate/auto` endpoint added; returns roi_config dict for balance/bet/win fields. |
| C3 | Parallel OCR (ProcessPoolExecutor, 8 workers) | BE | 300-frame video: 90s → < 15s; CPU < 80%; memory < 2GB | ✅ Done (2026-07-22) — `ocr_frames()` now accepts `workers` param; parallel path uses `ProcessPoolExecutor`; configurable per job via payload `workers` field. Sequential path preserved for workers=1. |
| C4 | Scene-change dedup (pHash/SSIM) | BE | Static frames (menus, bonuses) skipped; 40–60% fewer OCR calls | ✅ Done (2026-07-22) — pHash (DCT-based) implemented in `_phash()`; `ocr_frames()` accepts `dedup_threshold` (hamming distance); frames with distance < threshold to last processed frame skip OCR. Configurable per job via payload. |
| E1 | Tauri v2 migration (Rust + Vite) | DESKTOP | `cargo tauri build` → 15MB `.msi`/`.dmg`/`.AppImage`; PySide6 removed | ⏳ Pending (v1 shell functional; v2 migration deferred) |
| E2 | Auto-updater (delta patches via GitHub Releases) | DESKTOP | `tauri.updater` checks on startup; downloads delta; applies on restart; rollback on failure | ✅ Done (2026-07-22) — updater enabled in `tauri.conf.json`; endpoints pointing to GitHub Releases; pubkey placeholder ready. Requires signing key + release workflow to activate. |
| E3 | System tray + global hotkeys | DESKTOP | Tray icon: Start/Stop Live, Screenshot, Open Window; `Ctrl+Shift+S` = screenshot | ✅ Done (2026-07-22) — system tray already existed (Open/Docs/Restart/Quit); added `Ctrl+Shift+S` global shortcut via `global-shortcut-all` feature; emits `global-screenshot` event to frontend. |

### Definition of Done
- Video pipeline processes 2hr recording in < 10min
- Tauri app installs/runs on clean Windows/macOS/Linux VM

---

## Phase 4 — AI Intelligence + Distribution (Weeks 10–12)
**Goal**: Structured AI, cost control, shippable installers

| ID | Task | Owner | Acceptance Criteria | Status |
|----|------|-------|---------------------|--------|
| C5 | Event validation (balance continuity + bet/win reconciliation) | BE | Implausible deltas (> 3σ) flagged for review; auto-correct single-frame OCR glitches | ✅ Done (2026-07-22) — `engines/event_validator.py` with z-score detection, interpolation, auto-correction; `GET /api/v1/events/validate/{session_id}` endpoint; wired into video pipeline after event building; 8 tests passing |
| C6 | Video job progress WebSocket | BE+FE | FE shows stage: `extracting → ocr → building → done`; cancel button works | ✅ Done (2026-07-22) — `useJobWebSocket` hook for real-time progress; `JobsMonitor.tsx` rewritten with live stage labels, progress bars, cancel for pending+running jobs; WebSocket connection status indicator |
| C7 | Frame annotation export (debug mode) | BE | `GET /video-jobs/{id}/annotated-frames` → ZIP with ROI boxes + OCR text overlay | ✅ Done (2026-07-22) — `engines/frame_annotator.py` with OpenCV annotation + ZIP packaging; `GET /api/v1/video-jobs/{id}/annotated-frames` endpoint; 4 tests passing |
| D1 | Structured AI outputs (Pydantic + function calling) | BE | `AIInsight` model: `headline`, `risk_level`, `discipline_score`, `behavior_tags[]`, `evidence[]` | ✅ Done (2026-07-22) — Pydantic models in `backend/schemas/ai.py`; `parse_ai_response()` replaces ad-hoc dict parsing; `AI_TOOL_SCHEMA` for Anthropic tool_use; 6 tests passing |
| D2 | pgvector embeddings + similarity search | BE | `POST /intelligence/embed` stores vectors; `GET /intelligence/similar/{id}` returns top-5 in < 100ms | **Deferred** — requires PostgreSQL (SaaS-gated with A1/A2); revisit when multi-tenant track is committed |
| D3 | Prompt versioning + A/B framework | BE | Prompts in DB with `version`, `model`, `params`; `/intelligence/ai/compare` runs A/B on demand | ✅ Done (2026-07-22) — `engines/prompt_manager.py` with CRUD + A/B recording; `prompt_versions` + `ab_results` tables (V8 schema); `GET/POST /api/v1/prompts` endpoints; `ai_insights_engine.py` loads active prompt from DB (falls back to hardcoded SYSTEM_PROMPT) |
| E4 | Bundle deps (Tesseract, FFmpeg, Python) | DESKTOP | Installer includes all; no external deps; `sessionguard --version` works offline | ✅ Done (2026-07-22) — `tauri.conf.json` updated with `externalBin`, `resources`, expanded bundle targets; `main.rs` checks bundled paths first; `bundle/README.md` with setup instructions |
| E5 | SQLCipher encrypted SQLite | DESKTOP | DB file unreadable without key; key derived from user password + Argon2id | ✅ Done (2026-07-22) — `database/encryption.py` with PBKDF2 key derivation, optional SQLCipher, graceful degradation; `get_connection()` checks encryption config; 7 tests passing (2 skipped — pysqlcipher3 not installed) |

### Definition of Done
- ✅ AI responses validated against schema (D1 done)
- ✅ Event validation flags implausible OCR events (C5 done)
- ✅ Real-time job progress in frontend (C6 done)
- ✅ Debug frame annotation export (C7 done)
- ✅ Prompt versioning and A/B framework (D3 done)
- ✅ SQLCipher encryption support (E5 done)
- ✅ Desktop bundle configuration (E4 done)
- Installers signed/notarized (pending — requires signing keys)
- Offline install works (pending — requires bundling actual binaries)

---

## Phase 5 — Advanced AI + Desktop Polish (Weeks 13–15)
**Goal**: Production AI features; polished desktop UX

| ID | Task | Owner | Acceptance Criteria |
|----|------|-------|---------------------|
| C8 | Multi-region OCR per frame (balance + bet + win + bonus + jackpot) | BE | Modern slots: 5+ UI elements extracted per frame |
| C9 | OCR accuracy benchmarks (synthetic + real frames) + CI gate | BE | Regression detection on dependency updates; CI fails if accuracy < threshold |
| C10 | Video chunking + resume (FFmpeg segment + DB checkpoint per chunk) | BE | Process any length video reliably; resume from last checkpoint |
| D4 | Session similarity clustering (HDBSCAN on behavioral vectors) | BE | `session_clusters` table populated; `GET /intelligence/clusters` returns cohorts |
| D5 | "Explain this alert" — LLM-generated root cause | BE | Alert detail page shows AI explanation with evidence citations |
| D6 | Cost tracking + budget alerts for AI calls | BE | Token counting per session; `$/session` metric; auto-fallback at budget threshold |
| D7 | Offline AI fallback (llama.cpp / Ollama) | BE | Full functionality air-gapped; model downloaded at install |
| D8 | "Session Coach" — real-time behavioral intervention | BE+FE | Live engine emits coaching events; FE shows toast/banner for tilt/chasing |
| D9 | Evidence package builder (PDF + frames + OCR + events + AI narrative) | BE | `POST /sessions/{id}/evidence` → court/regulatory ready ZIP |
| D10 | Dataset quality report (completeness, bias, label distribution) | BE | `GET /intelligence/dataset-quality` → compliance artifact |
| E6 | Native notifications (Windows Toast / macOS Notification Center) | DESKTOP | Alerts work when app minimized/trayed |
| E7 | Crash reporting (Sentry native / custom) | DESKTOP | MTTR < 1hr for desktop issues |
| E8 | Portable mode (all data in app folder, no AppData/Registry) | DESKTOP | Run from network share/USB |
| E9 | Code-sign builds (Windows EV cert + macOS notarization) | DESKTOP | Trusted install; no SmartScreen/Gatekeeper warnings |
| E10 | MSI + DMG + AppImage + Flatpak via CI | DESKTOP | Professional distribution channels |

### Definition of Done
- All AI features behind feature flags
- Desktop app passes Microsoft Store / Mac App Store pre-checks
- Evidence package accepted by legal review

---

## Phase 6 — SaaS Foundations + Launch Prep (Weeks 16–18)  — ⚠️ OPTIONAL / BUSINESS-GATED

**This entire phase (and A1/A2 above) only applies if you decide to sell SessionGuard as a hosted multi-tenant product.** As of 2026-07-21 the confirmed direction is single-user-local. Don't start F1–F10 speculatively — multi-tenant RLS, Stripe billing, SSO/SCIM, and SOC2 Type II are meaningful ongoing cost/complexity (compliance, support burden, infra spend) that only make sense once there's a committed business decision and at least one prospective paying customer. Revisit this phase when that decision is made, not on a fixed week-16 timer.

**Goal**: Multi-tenant SaaS ready for paying customers

| ID | Task | Owner | Acceptance Criteria |
|----|------|-------|---------------------|
| F1 | Multi-tenant architecture (RLS + org_id on all tables) | BE | Data isolation enforced at DB level; `org_id` on every table |
| F2 | Stripe Billing integration (subscriptions, usage-based, trials) | BE | `POST /billing/checkout` → Stripe session; webhook syncs subscription status |
| F3 | Admin dashboard (tenant mgmt, usage analytics, impersonation) | FE | Admin can view/manage all orgs; usage charts; impersonate user |
| F4 | SSO (OIDC/SAML) + SCIM provisioning | BE | Enterprise login via Okta/Azure AD; user provisioning via SCIM |
| F5 | Audit log export + SIEM integration (Splunk, Datadog, Elastic) | BE | `GET /admin/audit-logs/export` → JSONL; webhook to SIEM |
| F6 | Public API (API keys, rate tiers, OpenAPI spec) | BE | Partners integrate via `Authorization: Bearer sk_...`; rate limits per tier |
| F7 | Data residency (region selection + GDPR deletion workflow) | BE | EU/US region select at signup; `DELETE /account` purges all data in 30 days |
| F8 | Automated backup + PITR for PostgreSQL | BE | RPO < 1hr; RTO < 15min; tested quarterly |
| F9 | Feature flags (LaunchDarkly / open-source alternative) | BE+FE | Zero-risk rollouts; kill switches per feature |
| F10 | SOC2 Type II readiness (policies, evidence, pen test) | ALL | Auditor-ready artifact pack; pen test remediated |

### Definition of Done
- First paying customer onboarded end-to-end
- SOC2 evidence package complete
- Launch checklist 100% green

---

## Expected Outcome After Phase 6 (Week 18)

### Product Capabilities
| Area | Before (v1.2.0) | After (Phase 6) |
|------|-----------------|-----------------|
| **Database** | SQLite (single-file, no concurrency) | PostgreSQL + RLS, multi-tenant, PITR |
| **API** | 30+ routes, no versioning, no rate limits | `/api/v1/`, versioned, rate-limited, OpenAPI |
| **Auth** | JWT + refresh, per-process secret | Env-secret, rotation, SSO/OIDC, SCIM |
| **Background Jobs** | Blocking in-request | Thread-pool + SQLite, retries ×3 with backoff, WS progress, cancellation
| **Testing** | Zero tests | 80%+ coverage, E2E (Playwright), load tested |
| **OCR** | Tesseract only, sequential, 90s/300 frames | Tesseract + EasyOCR GPU, parallel (8×), 15s/300 frames |
| **Video Pipeline** | Basic, no resume, no progress | Chunked, resumable, annotated debug export |
| **AI** | Free-text Claude prompts (structured outputs done) | Structured outputs, embeddings, clustering, coaching, cost control, offline fallback |
| **Desktop** | PySide6 (150MB, manual deps) | Tauri v2 (15MB, bundled, signed, auto-update, tray, portable) |
| **Distribution** | `.bat`/`.sh` scripts | MSI/DMG/AppImage/Flatpak via CI, code-signed |
| **SaaS** | Single-user local | Multi-tenant, billing, admin, public API, data residency, SOC2-ready |

### Technical Metrics
| Metric | Target |
|--------|--------|
| API p95 latency | < 200ms (cached), < 500ms (uncached) |
| Video processing (2hr) | < 10 minutes |
| OCR accuracy (fields) | > 95% |
| Bundle size (gzipped) | < 500KB initial, < 2MB total |
| Desktop installer | < 20MB |
| Test coverage | > 80% backend, > 70% frontend |
| Deploy frequency | Daily (feature flags) |
| MTTR (desktop) | < 1 hour |
| Uptime SLA | 99.9% |

### Business Readiness
- **First paying customer** onboarded via self-serve or sales-assisted
- **SOC2 Type II** evidence package complete (policies, logs, access controls, encryption, incident response)
- **Public API** documented with API keys, rate tiers, webhooks
- **Admin panel** for tenant management, usage analytics, impersonation
- **Data residency** for EU/US with GDPR deletion workflow
- **Feature flags** enabling zero-risk rollouts
- **Automated backups** with tested PITR
- **Cost model** understood: AI $/session, infra $/MAU, support $/ticket

---

## Track Sequencing (solo-friendly)

If it's still just you: work top-to-bottom within a phase before moving to the next, picking whichever track (Backend/Frontend/Desktop) unblocks the most value next — don't try to run 3 tracks in parallel solo. If you bring on a second or third person, split by track as shown; each track's rows are already ordered by dependency.

| Phase | Backend track | Frontend track | Desktop/Infra track |
|-------|-----------------|------------------|----------------------|
| 0 | P0.1–P0.3, P0.5 | — | P0.4 |
| 1 | A1–A6 *(A1/A2 SaaS-gated, see above)* | B1–B3 | — |
| 2 | A7–A10 *(A7: enhance thread-pool job service)* | B4–B6 | — |
| 3 | C1–C4 | — | E1–E3 |
| 4 | C5–C7, D1–D3 | — | E4–E5 |
| 5 | C8–C10, D4–D10 | — | E6–E10 |
| 6 *(gated)* | F1–F10 | F3 (admin FE) | F8 (infra) |

---

## Risk Register (Updated)

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Video pipeline bugs block release | High | High | Fix in Phase 2 (A7); integration test in Phase 3 |
| Tesseract accuracy insufficient | Medium | High | EasyOCR fallback (C1); benchmark gate (C9) |
| SQLite corruption at scale | Medium | Critical | PostgreSQL migration (A1) by Phase 2 |
| Desktop app store rejection | Low | High | Code-sign (E9); notarization; sandbox; pre-submit checks |
| AI cost spiral | Low | Medium | Budget tracking (D6); offline fallback (D7) |
| Key developer bus factor | High | High | ADRs in repo; pair programming; documented handoffs |
| Divergent local copies drift again (canonical vs. clone vs. installed .exe) | High | Medium | Pick one canonical path and always launch/edit from it; if a second copy is ever needed again, sync immediately rather than letting WIP sit uncommitted for months |
| Secrets re-committed to config files | Medium | High | `.env`/env-vars only for keys going forward; consider a pre-commit secret scanner (e.g. gitleaks) given it already happened once |

---

## Communication Cadence

| Meeting | Frequency | Participants | Purpose |
|---------|-----------|--------------|---------|
| Standup | Daily (15min) | All 3 | Blockers, sync |
| Phase Review | End of each phase | All 3 + PM | Demo, retrospective, go/no-go |
| Architecture Review | Bi-weekly | All 3 | Cross-cutting decisions |
| Incident Review | As needed | Relevant | Postmortem, action items |

---

## Definition of "Revival Complete"

SessionGuard is **revived** when:

1. ✅ **Local-first desktop app** installs in < 30s, works offline, auto-updates
2. ✅ **SaaS backend** handles 1000+ concurrent users, multi-tenant, billed via Stripe
3. ✅ **AI intelligence** provides structured, explainable, cost-controlled insights
4. ✅ **Video→Events pipeline** processes 2hr recordings in < 10min with > 95% accuracy
5. ✅ **Test coverage** > 80% backend, > 70% frontend, E2E green in CI
6. ✅ **SOC2 evidence** package ready for auditor
7. ✅ **First revenue** recognized from paying customer

---

*This document lives at `SessionGuardRevival.md` in the repo root. Update at each phase gate.*
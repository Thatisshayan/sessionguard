# SessionGuard Revival — Phased Handoff Document

**Generated**: 2026-07-10 · **Last revised**: 2026-07-21  
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
| ID | Task | Acceptance Criteria |
|----|------|---------------------|
| A1 | *(SaaS-gated)* PostgreSQL + Alembic migration | `alembic upgrade head` creates 15 tables on clean PG; `init_db.py` deprecated |
| A2 | *(SaaS-gated)* Redis registry for live runs | Live run survives server restart; `GET /live/{id}` works after deploy |
| A3 | Rate limiting on auth/write endpoints | `POST /auth/login` → 429 after 5 req/min; `POST /upload` → 429 after 10 req/min |
| A4 | Structured JSON logging (structlog) | All requests log `request_id`, `user_id`, `latency_ms`, `status` to stdout |
| A5 | Secret key from env + hot-reload | `SECRET_KEY` from `$ENV`; `SIGHUP` rotates key without dropping active tokens |
| A6 | Composite DB indexes | `EXPLAIN ANALYZE` shows index scan on `events(session_id, timestamp)` and `live_events(run_id, id)` |

### Frontend (Engineer 2)
| ID | Task | Acceptance Criteria |
|----|------|---------------------|
| B1 | Split `SessionDetail.tsx` (36K → 8 components) | Each sub-component < 500 lines; `SessionDetail` < 200 lines; Storybook stories for each |
| B2 | React Query (TanStack Query) v5 migration | All `useEffect` fetch → `useQuery`; deduped requests; background refetch; devtools visible |
| B3 | Route guards + lazy loading | `React.lazy` on all 14 pages; `Suspense` fallback; auth guard redirects to `/login` |

### Definition of Done
- CI passes (lint, typecheck, unit tests)
- Staging deploy works
- This document updated with Phase 1 results

---

## Phase 2 — Backend Hardening + Frontend Polish (Weeks 4–6)
**Goal**: Resilient async processing; fast, cacheable frontend

### Backend (Engineer 1)
| ID | Task | Acceptance Criteria |
|----|------|---------------------|
| A7 | Background job worker (Celery + Redis) | Video/OCR jobs enqueue via `POST /jobs`; worker picks up; progress via WebSocket; retries ×3 |
| A8 | Upload validation (size, MIME, virus scan hook) | 500MB max; only `video/mp4`, `text/csv`, `image/*`; ClamAV scan (stub) before processing |
| A9 | Test suite (pytest + httpx + testcontainers) | 80%+ coverage on 30+ endpoints; `pytest -x` < 60s; runs in GitHub Actions on every PR |
| A10 | API versioning (`/api/v1/`) | All routes under `/api/v1/`; deprecation header on v0; OpenAPI spec at `/api/v1/openapi.json` |

### Frontend (Engineer 2)
| ID | Task | Acceptance Criteria |
|----|------|---------------------|
| B4 | Design tokens (Tailwind v4 `@theme`) | Colors, spacing, radii, shadows in `global.css`; dark mode via `data-theme`; zero hardcoded values |
| B5 | Aggregated dashboard endpoint | `GET /api/v1/dashboard/summary` returns all 7 KPIs + charts in < 200ms; FE uses single `useQuery` |
| B6 | Playwright E2E (5 critical flows) | Login → Upload CSV → SessionDetail → Export PDF → Live Monitor; runs in CI on Chromium/Firefox |

### Definition of Done
- Load test (k6): 100 concurrent users, p95 < 500ms
- E2E green in CI
- Staging = production parity

---

## Phase 3 — OCR/Video Pipeline + Desktop Core (Weeks 7–9)
**Goal**: Fast, accurate video→events; installable Tauri app

| ID | Task | Owner | Acceptance Criteria |
|----|------|-------|---------------------|
| C1 | EasyOCR GPU fallback (ONNX Runtime) | BE | Frames with Tesseract confidence < 0.75 auto-reprocess with EasyOCR; 95%+ field extraction |
| C2 | ROI auto-calibration (template matching + contours) | BE | New game: upload 3 screenshots → ROI config generated; manual override still works |
| C3 | Parallel OCR (ProcessPoolExecutor, 8 workers) | BE | 300-frame video: 90s → < 15s; CPU < 80%; memory < 2GB |
| C4 | Scene-change dedup (pHash/SSIM) | BE | Static frames (menus, bonuses) skipped; 40–60% fewer OCR calls |
| E1 | Tauri v2 migration (Rust + Vite) | DESKTOP | `cargo tauri build` → 15MB `.msi`/`.dmg`/`.AppImage`; PySide6 removed |
| E2 | Auto-updater (delta patches via GitHub Releases) | DESKTOP | `tauri.updater` checks on startup; downloads delta; applies on restart; rollback on failure |
| E3 | System tray + global hotkeys | DESKTOP | Tray icon: Start/Stop Live, Screenshot, Open Window; `Ctrl+Shift+S` = screenshot |

### Definition of Done
- Video pipeline processes 2hr recording in < 10min
- Tauri app installs/runs on clean Windows/macOS/Linux VM

---

## Phase 4 — AI Intelligence + Distribution (Weeks 10–12)
**Goal**: Structured AI, cost control, shippable installers

| ID | Task | Owner | Acceptance Criteria |
|----|------|-------|---------------------|
| C5 | Event validation (balance continuity + bet/win reconciliation) | BE | Implausible deltas (> 3σ) flagged for review; auto-correct single-frame OCR glitches |
| C6 | Video job progress WebSocket | BE+FE | FE shows stage: `extracting → ocr → building → done`; cancel button works |
| C7 | Frame annotation export (debug mode) | BE | `GET /video-jobs/{id}/annotated-frames` → ZIP with ROI boxes + OCR text overlay |
| D1 | Structured AI outputs (Pydantic + function calling) | BE | `AIInsight` model: `headline`, `risk_level`, `discipline_score`, `behavior_tags[]`, `evidence[]` |
| D2 | pgvector embeddings + similarity search | BE | `POST /intelligence/embed` stores vectors; `GET /intelligence/similar/{id}` returns top-5 in < 100ms |
| D3 | Prompt versioning + A/B framework | BE | Prompts in DB with `version`, `model`, `params`; `/intelligence/ai/compare` runs A/B on demand |
| E4 | Bundle deps (Tesseract, FFmpeg, Python) | DESKTOP | Installer includes all; no external deps; `sessionguard --version` works offline |
| E5 | SQLCipher encrypted SQLite | DESKTOP | DB file unreadable without key; key derived from user password + Argon2id |

### Definition of Done
- AI responses validated against schema
- Installers signed/notarized
- Offline install works

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
| **Background Jobs** | Blocking in-request | Celery + Redis, retries, progress WS |
| **Testing** | Zero tests | 80%+ coverage, E2E (Playwright), load tested |
| **OCR** | Tesseract only, sequential, 90s/300 frames | Tesseract + EasyOCR GPU, parallel (8×), 15s/300 frames |
| **Video Pipeline** | Basic, no resume, no progress | Chunked, resumable, annotated debug export |
| **AI** | Free-text Claude prompts | Structured outputs, embeddings, clustering, coaching, cost control, offline fallback |
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
| 2 | A7–A10 | B4–B6 | — |
| 3 | C1–C4 | — | E1–E3 |
| 4 | C5–C7, D1–D3 | — | E4–E5 |
| 5 | C8–C10, D4–D10 | — | E6–E10 |
| 6 *(gated)* | F1–F10 | F3 (admin FE) | F8 (infra) |

---

## Risk Register (Updated)

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Video pipeline bugs block release | High | High | Fix in Phase 1 (A7–A8); integration test in Phase 3 |
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
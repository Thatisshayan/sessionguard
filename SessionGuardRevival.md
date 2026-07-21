# SessionGuard Revival — 6-Phase Handoff Document

**Generated**: 2026-07-10  
**Base Commit**: `4b4c417` (audit report) / `fd797d7` (v1.2.0)  
**Target**: Production-ready SaaS + Desktop app in 18 weeks (3 engineers)

---

## Phase 1 — Foundations (Weeks 1–3)
**Goal**: Stable, observable, testable backend + frontend data layer

| ID | Task | Owner | Acceptance Criteria |
|----|------|-------|---------------------|
| A1 | PostgreSQL + Alembic migration | BE | `alembic upgrade head` creates 15 tables on clean PG; `init_db.py` deprecated |
| A2 | Redis registry for live runs | BE | Live run survives server restart; `GET /live/{id}` works after deploy |
| A3 | Rate limiting on auth/write endpoints | BE | `POST /auth/login` → 429 after 5 req/min; `POST /upload` → 429 after 10 req/min |
| A4 | Structured JSON logging (structlog) | BE | All requests log `request_id`, `user_id`, `latency_ms`, `status` to stdout |
| A5 | Secret key from env + hot-reload | BE | `SECRET_KEY` from `$ENV`; `SIGHUP` rotates key without dropping active tokens |
| A6 | Composite DB indexes | BE | `EXPLAIN ANALYZE` shows index scan on `events(session_id, timestamp)` and `live_events(run_id, id)` |
| B1 | Split `SessionDetail.tsx` (36K → 8 components) | FE | Each sub-component < 500 lines; `SessionDetail` < 200 lines; Storybook stories for each |
| B2 | React Query (TanStack Query) v5 migration | FE | All `useEffect` fetch → `useQuery`; deduped requests; background refetch; devtools visible |
| B3 | Route guards + lazy loading | FE | `React.lazy` on all 14 pages; `Suspense` fallback; auth guard redirects to `/login` |

**Definition of Done**: CI passes (lint, typecheck, unit tests); staging deploy works; audit report `SessionGuardRevival.md` updated with Phase 1 results.

---

## Phase 2 — Backend Hardening + Frontend Polish (Weeks 4–6)
**Goal**: Resilient async processing; fast, cacheable frontend

| ID | Task | Owner | Acceptance Criteria |
|----|------|-------|---------------------|
| A7 | Background job worker (Celery + Redis) | BE | Video/OCR jobs enqueue via `POST /jobs`; worker picks up; progress via WebSocket; retries ×3 |
| A8 | Upload validation (size, MIME, virus scan hook) | BE | 500MB max; only `video/mp4`, `text/csv`, `image/*`; ClamAV scan (stub) before processing |
| A9 | Test suite (pytest + httpx + testcontainers) | BE | 80%+ coverage on 30+ endpoints; `pytest -x` < 60s; runs in GitHub Actions on every PR |
| A10 | API versioning (`/api/v1/`) | BE | All routes under `/api/v1/`; deprecation header on v0; OpenAPI spec at `/api/v1/openapi.json` |
| B4 | Design tokens (Tailwind v4 `@theme`) | FE | Colors, spacing, radii, shadows in `global.css`; dark mode via `data-theme`; zero hardcoded values |
| B5 | Aggregated dashboard endpoint | BE+FE | `GET /api/v1/dashboard/summary` returns all 7 KPIs + charts in < 200ms; FE uses single `useQuery` |
| B6 | Playwright E2E (5 critical flows) | FE | Login → Upload CSV → SessionDetail → Export PDF → Live Monitor; runs in CI on Chromium/Firefox |

**Definition of Done**: Load test (k6) — 100 concurrent users, p95 < 500ms; E2E green in CI; staging = production parity.

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

**Definition of Done**: Video pipeline processes 2hr recording in < 10min; Tauri app installs/runs on clean Windows/macOS/Linux VM.

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

**Definition of Done**: AI responses validated against schema; installers signed/notarized; offline install works.

---

## Phase 5 — Advanced AI + Desktop Polish (Weeks 13–15)
**Goal**: Differentiated intelligence; professional desktop experience

| ID | Task | Owner | Acceptance Criteria |
|----|------|-------|---------------------|
| C8 | Multi-region OCR (balance, bet, win, bonus, jackpot) | BE | 5 fields/frame; config per game profile; benchmark shows 90%+ accuracy on test set |
| C9 | OCR benchmark CI gate | BE | Synthetic + 50 real frames; `pytest` fails if field accuracy < 88% |
| C10 | Video chunking + resume (FFmpeg segments + DB checkpoints) | BE | 4hr video → 15min chunks; kill -9 at 50% → resume from last checkpoint |
| D4 | HDBSCAN session clustering | BE | `GET /intelligence/clusters` returns labeled groups; silhouette > 0.5 |
| D5 | Alert explanations (LLM root-cause) | BE | `GET /alerts/{id}/explain` → "RTP 82% driven by 18-spin losing streak on spins 45–62" |
| D6 | AI cost tracking + budget alerts | BE | `/intelligence/ai/usage` shows $/session; Slack webhook on > $50/day |
| E6 | Native notifications (Windows Toast / macOS UserNotification) | DESKTOP | Alert fires → OS notification appears even when app minimized |
| E7 | Crash reporting (Sentry native) | DESKTOP | Minidump uploaded; `sentry-cli` symbolicate; dashboard shows crash-free users % |
| E8 | Portable mode (all data in app folder) | DESKTOP | `--portable` flag; runs from USB; no AppData/Registry writes |
| E9 | Code-sign (EV cert + Apple notarization) | DESKTOP | Windows SmartScreen "Publisher: SessionGuard Inc."; macOS `spctl -a -v` passes |
| E10 | Multi-format CI (MSI, DMG, AppImage, Flatpak) | DESKTOP | GitHub Actions matrix builds all 4; artifacts uploaded to Release draft |

**Definition of Done**: All installers pass Windows Defender / Gatekeeper; crash reports visible in Sentry; portable mode tested on 3 machines.

---

## Phase 6 — Integration + Launch Readiness (Weeks 16–18)
**Goal**: End-to-end polish; production hardening; docs

| ID | Task | Owner | Acceptance Criteria |
|----|------|-------|---------------------|
| D7 | Offline AI fallback (Ollama/llama.cpp) | BE | `AI_PROVIDER=ollama` → local Llama-3.1-8B; same schema; 3× slower but free |
| D8 | Session Coach (real-time intervention) | BE+FE | Live monitor: "Bet escalation detected — consider pause" toast + haptic (desktop) |
| D9 | Evidence package builder (court-ready PDF + frames + AI narrative) | BE | `POST /sessions/{id}/evidence` → PDF with hash chain, timeline, OCR frames, AI verdict |
| D10 | Dataset quality report | BE | `/intelligence/dataset-quality` → completeness %, label dist, bias metrics, drift alert |
| B7 | Virtualized lists (react-window) | FE | 10,000 sessions scroll at 60fps; `<FixedSizeList>` for sessions, events, review queue |
| B8 | WebSocket hook for live updates | FE | `useLiveEvents(runId)` replaces polling; reconnects on disconnect; < 100ms latency |
| B9 | Full A11y/ARIA audit (axe-core CI) | FE | `npm run a11y` → 0 violations WCAG 2.2 AA; screen reader tested (NVDA, VoiceOver) |
| B10 | Error boundaries + sonner toasts | FE | Uncaught error → friendly modal + "Report" button; toasts for all mutations |
| A9-final | Contract tests (Pact) for API | BE+FE | Consumer-driven contracts; CI fails if FE expects field BE removed |
| — | **Production runbook** | ALL | `RUNBOOK.md`: deploy, rollback, scale, incident response, on-call rotation |

**Definition of Done**: **Launch Criteria Met**
- ✅ All Phases 1–6 acceptance criteria green
- ✅ Load test: 500 concurrent users, p99 < 1s, 0 errors
- ✅ Security audit: 0 critical, ≤ 3 medium (all with mitigation)
- ✅ Accessibility: WCAG 2.2 AA certified
- ✅ Installers signed, notarized, uploaded to GitHub Releases
- ✅ Documentation: API docs, user guide, admin guide, runbook
- ✅ Monitoring: Grafana dashboards (API, DB, workers, AI costs), alerts on PagerDuty

---

## Expected Outcome After Phase 6

| Dimension | Before (v1.2.0) | After (v2.0.0 "Revival") |
|-----------|-----------------|--------------------------|
| **Architecture** | SQLite, in-memory state, monolithic FE | PostgreSQL + Redis, horizontal workers, React Query + WebSockets |
| **Reliability** | No tests, crashes lose live runs | 80%+ coverage, crash reporting, auto-recovery, zero-downtime deploys |
| **Performance** | 90s/video, 7 parallel API calls, 2.5MB bundle | < 10min/video (8×), 1 aggregated call, < 500KB initial JS |
| **Intelligence** | Rule-based insights, free-text AI | Structured AI, embeddings, clustering, real-time coaching, evidence packages |
| **Distribution** | Manual scripts, PySide6 (150MB), unsigned | CI-built MSI/DMG/AppImage/Flatpak (15MB), code-signed, auto-updater |
| **Security** | No rate limit, rotating secret breaks auth, world-readable DB | Rate limited, env secrets + rotation, encrypted DB, SOC2-ready audit log |
| **Accessibility** | Mouse-only, no ARIA | WCAG 2.2 AA, keyboard nav, screen readers, high contrast |
| **Observability** | `print()` statements | Structured logs, metrics, traces, dashboards, alerts |
| **Team Velocity** | Fragile, hard to onboard | Contract-tested API, component library, documented runbooks, < 1hr new dev setup |

**Shippable Artifacts**:
1. **SessionGuard Server** — Docker image (`ghcr.io/thatisshayan/sessionguard-api:v2.0.0`) + Helm chart
2. **SessionGuard Desktop** — Signed installers for Windows/macOS/Linux + auto-updater
3. **SessionGuard Web** — Static export (`dist/`) deployable to Vercel/Netlify/Cloudflare Pages
4. **Documentation** — `/docs` (OpenAPI, user guide, admin guide, runbook, architecture decision records)

---

## Handoff Checklist Per Phase

| Phase | BE Handoff | FE Handoff | Desktop Handoff | Shared |
|-------|------------|------------|-----------------|--------|
| 1 | PG schema, Redis, logging, indexes | Component library, QueryClient, AuthContext | Tauri scaffold, Rust toolchain | CI pipeline, `.env.example`, `RUNBOOK.md` v0.1 |
| 2 | Celery worker, OpenAPI v1, test suite | Tailwind tokens, Dashboard page, E2E suite | — | Load test results, staging URL |
| 3 | EasyOCR service, ROI calibrator, parallel OCR | — | Tauri v2 build, updater, tray | Video pipeline benchmarks |
| 4 | Structured AI, pgvector, prompt versioning | Annotated frames viewer | Bundled deps, SQLCipher | Installer signing certs |
| 5 | Multi-region OCR, clustering, alert explain | Virtualized lists, WS hook, A11y | Notifications, crash reporting, portable | Release artifacts matrix |
| 6 | Offline AI, Coach, Evidence, Dataset QA | Error boundaries, toasts, contract tests | Code-sign, multi-format CI, notarization | **Launch Sign-off**, Runbook v1.0 |

---

## Risk Mitigation

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Tauri v2 migration blockers | Medium | High | Spike in Week 1; fallback: keep PySide6 for v2.0, migrate v2.1 |
| EasyOCR GPU compatibility | Medium | Medium | CPU fallback; ONNX Runtime CPU is fast enough for < 15s/video |
| pgvector not in managed PG (RDS) | Low | High | Use `pgvector` extension on Cloud SQL / Neon / Supabase; or `pg_embedding` |
| Code-sign cert delays | Medium | Medium | Order EV cert Week 1; use self-signed for dev; GitHub Actions `apple-cert` action |
| AI cost overrun | Low | High | Hard budget in `D6`; fallback to local model `D7`; alert at 50% budget |
| Scope creep | High | Medium | **Fixed scope per phase**; new items → backlog for v2.1 |

---

## Communication Cadence

| Meeting | Frequency | Attendees | Purpose |
|---------|-----------|-----------|---------|
| Standup | Daily 15min | All | Blockers, sync |
| Phase Review | End of phase | All + PM | Demo, retro, go/no-go next phase |
| Architecture Sync | Weekly 30min | BE + Desktop | Cross-cutting concerns (DB, Redis, API) |
| FE/Desktop Sync | Weekly 30min | FE + Desktop | Tauri ↔ React integration, shared types |
| Security Review | Phase 2, 4, 6 | BE + Sec | Threat model, pen test findings |

---

## Success Metrics (Post-Launch, 30 Days)

| Metric | Target |
|--------|--------|
| Crash-free sessions (desktop) | > 99.5% |
| API p99 latency | < 500ms |
| Video pipeline success rate | > 95% |
| AI cost per session | < $0.10 |
| Installer download → first session | < 5 min |
| User-reported bugs (critical) | 0 |
| Accessibility score (axe) | 100% |

---

*End of Handoff Document — Update at each Phase Review*
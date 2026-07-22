# SessionGuard v1.5.0 — Local-First Session Intelligence Platform

Universal session intelligence for casino/slot analysis. Real OCR (Tesseract 5), behavior pattern detection (scikit-learn), live screen monitoring, video→event pipelines, AI narrative insights (NVIDIA NIM + Ollama offline fallback), multi-format exports, evidence packages with hash manifests. Desktop + Web.

> **Current project status**: see [`SessionGuardRevival.md`](SessionGuardRevival.md) — **Phases 0–5 all complete** (2026-07-22). 72 tests passing, 0 TS errors. Phase 6 (SaaS) is business-gated/deferred. For a point-in-time code audit, see [`10072026auditbytopencode.md`](10072026auditbytopencode.md) (dated 2026-07-10 — check the revival doc for anything more recent).

---

## Quick Start

### 1. First-time setup

```bash
# Windows
scripts\setup.bat

# Mac / Linux
bash scripts/setup.sh
```

### 2. Start everything

```bash
# Windows
scripts\run_all.bat

# Mac / Linux
bash scripts/run_all.sh
```

### 3. Open

| Service | URL |
|---------|-----|
| Dashboard | http://localhost:5173 |
| API Docs | http://127.0.0.1:8000/docs |
| Desktop App | Launched by run_all |

---

## Dependencies

| Dependency | Required | Purpose | Install |
|------------|----------|---------|---------|
| Python 3.11+ | ✅ | Backend + engines | https://python.org |
| Node.js 18+ | ✅ | React frontend | https://nodejs.org |
| FFmpeg | ✅ Video | Frame extraction | https://ffmpeg.org/download.html |
| Tesseract 5 | ✅ OCR | Field extraction from frames | https://github.com/tesseract-ocr |
| Ollama | ➕ | Offline AI fallback (air-gapped mode) | https://ollama.ai |
| EasyOCR (optional) | ➕ | GPU-accelerated OCR backup | `pip install easyocr` |
| Tauri CLI | ➕ | Desktop build | `cargo install tauri-cli` |
| HDBSCAN (optional) | ➕ | Advanced clustering | `pip install hdbscan` |

## Environment Variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `NVIDIA_API_KEY` | — | NVIDIA NIM API key (required for NVIDIA, falls back to Ollama/rule-based if unset) |
| `SG_AI_BUDGET_USD` | `0.001` | Daily AI cost budget — auto-fallback to Ollama when exceeded |
| `SG_DATA_DIR` | — | Portable mode data directory (set by `--portable` flag) |
| `SG_DB_PASSWORD` | — | SQLCipher encryption password (if encryption enabled) |
| `VITE_SENTRY_DSN` | — | Sentry DSN for frontend crash reporting |
| `SENTRY_DSN` | — | Sentry DSN for desktop (Tauri/Rust) crash reporting |
| `SECRET_KEY` | random | JWT signing secret — set explicitly for production |

---

## Architecture

```
sessionguard/
├── backend/                      # FastAPI application (30+ endpoints)
│   ├── main.py                   # App factory — 22 route groups registered
│   ├── routes/                   # One file per endpoint group
│   │   ├── health, sessions, metrics, insights, alerts, review_queue
│   │   ├── uploads, exports, compare, profiles, video_status, ocr_status
│   │   ├── events, behavior, live, auth, projects, jobs, admin
│   │   ├── parser_benchmark, ws, notes, evidence, recorder
│   │   ├── openapi_export, system_config, data_export, trends
│   │   ├── search, tags, intelligence, coach, ocr_calibrate, updater
│   ├── auth/service.py           # PBKDF2-SHA256 + JWT (access 60m, refresh 30d)
│   └── services/                 # csv_parser, export_service, evidence_package
├── engines/                      # Core business logic (15 engines)
│   ├── analysis_engine.py        # Global KPIs, RTP distribution, net-over-time, by-game
│   ├── insights_engine.py        # Rule-based insight generation
│   ├── alerts_engine.py          # Threshold alerts — RTP, loss, streak
│   ├── review_queue_engine.py    # Uncertain-first queue
│   ├── comparison_engine.py      # Multi-session diff + narrative
│   ├── behavior_engine.py        # 5 sklearn patterns (tilt, drift, escalation, chasing, volatility)
│   ├── ocr_engine.py             # Tesseract 5 — ROI crop, preprocessing, field extraction (5 fields)
│   ├── video_pipeline.py         # FFmpeg → cv2 frames → OCR → events → review queue (chunked, resumable)
│   ├── live_engine.py            # Mock + screen mode with thread lifecycle
│   ├── live_coach_engine.py      # Real-time behavioral intervention coaching
│   ├── ai_insights_engine.py     # NVIDIA NIM narrative + risk scoring + cost tracking + Ollama fallback
│   ├── offline_ai.py             # Ollama local LLM integration (offline AI fallback)
│   ├── prompt_manager.py         # Prompt versioning + A/B testing framework
│   ├── cluster_engine.py         # Session similarity clustering (HDBSCAN optional, cosine fallback)
│   ├── event_validator.py        # Z-score balance continuity + bet/win reconciliation
│   ├── frame_annotator.py        # OpenCV frame annotation with ROI boxes + OCR text overlay
│   └── dataset_quality.py        # Dataset completeness/bias/distribution metrics
├── frontend/                     # React 18 + TypeScript + Vite
│   ├── src/pages/                # 14 pages
│   │   ├── Dashboard, Sessions, SessionDetail, LiveMonitor, Compare
│   │   ├── Upload, ReviewQueue, Reports, Profiles, Settings
│   │   ├── ParserBenchmark, JobsMonitor, Admin, Login
│   ├── src/services/api.ts       # 90+ typed API functions (single source of truth)
│   ├── src/store/appStore.ts     # Zustand-like store (error, loading, user, sessions)
│   └── src/components/           # 8 shared components
├── desktop_app/                  # PySide6 embedded browser shell (legacy)
├── desktop_shell/                # Tauri v2 (Rust) native build — primary desktop target
├── database/                     # SQLite + 5 schema migrations (15 tables)
│   └── db.py                     # WAL mode, FK enforcement, versioned init_db_vN()
├── config/                       # app_config.json + per-game OCR profiles
└── scripts/                      # Cross-platform .bat + .sh for setup, run_all, seed_db
```

---

## API Reference (40+ Endpoints)

| Group | Key Endpoints |
|-------|---------------|
| Health | `GET /health`, `GET /health/detailed` |
| Auth | `POST /auth/login`, `POST /auth/signup`, `POST /auth/refresh`, `GET /auth/me` |
| Sessions | `GET/POST/PATCH/DELETE /sessions`, `GET /sessions/{id}`, `GET /sessions/{id}/ocr-results` |
| Metrics | `GET /metrics`, `/rtp-distribution`, `/net-over-time`, `/by-game`, `/session/{id}` |
| Insights | `GET /insights`, `POST /insights/{id}/regenerate` |
| Alerts | `GET /alerts`, `GET /alerts/summary`, `PATCH /alerts/{id}/acknowledge`, `GET /alerts/{id}/explain` (D5) |
| Review Queue | `GET /review-queue`, `GET /review-queue/summary`, `PATCH /review-queue/{id}/resolve` |
| Upload | `POST /upload`, `GET /upload`, `GET /upload/template/{type}` |
| Exports | `POST /exports`, `GET /exports`, `GET /exports/{id}/download` |
| Evidence | `GET /sessions/{id}/evidence/verify` (D9 — hash manifest verification) |
| Compare | `POST /compare` |
| Events | `GET /events`, `GET /events/summary`, `GET /events/validate/{session_id}` (C5) |
| Behavior | `GET /behavior/session/{id}`, `GET /behavior/global` |
| Live | `POST /live/start`, `POST /live/{id}/pause`, `POST /live/{id}/resume`, `POST /live/{id}/stop`, `GET /live/{id}/events` |
| Projects | `GET/POST/DELETE /projects` |
| Jobs | `GET/POST /jobs`, `GET /jobs/{id}`, `POST /jobs/{id}/cancel`, `GET /jobs/worker/health` |
| Admin | `GET /admin/system-health`, `GET /admin/system-stats`, `GET /admin/audit-log` |
| Intelligence | `POST /intelligence/clusters/build`, `GET /intelligence/clusters`, `GET /intelligence/anomalies`, `GET /intelligence/dataset-quality` (D10) |
| AI Coach | `GET /intelligence/ai/status`, `GET /intelligence/ai/session/{id}`, `POST /intelligence/ai/compare` |
| AI Cost | `GET /api/v1/ai-cost/usage` (D6 — token usage + budget tracking) |
| Prompts | `GET/POST /api/v1/prompts` (D3 — prompt versioning + A/B) |
| OCR Calibrate | `POST /ocr/process`, `POST /ocr/calibrate`, `POST /ocr-calibrate/auto` (C2), `GET /ocr/status` |
| Video Jobs | `GET /video-jobs`, `GET /video-jobs/{id}/annotated-frames` (C7) |
| Updater | `GET /updater/check`, `GET /updater/current-version`, `POST /updater/dismiss` |
| Video Status | `GET /video-status`, `GET /ocr-status` |
| WebSocket | `WS /ws/connections`, `WS /ws/global` |

---

## Feature Completeness

| Feature | Backend | Frontend | Desktop | Tests | Docs |
|---------|---------|----------|---------|-------|------|
| Session CRUD | ✅ | ✅ | ✅ | ✅ | ✅ |
| CSV Upload (spin/session) | ✅ | ✅ | ✅ | ✅ | ✅ |
| OCR Engine (Tesseract, 5 fields) | ✅ | ✅ | ✅ | ✅ | ✅ |
| Video Pipeline (chunked, resumable) | ✅ | ✅ | ⚠️ | ✅ | ✅ |
| Behavior Analysis (5 patterns) | ✅ | ✅ | ✅ | ✅ | ✅ |
| Live Monitor (mock) | ✅ | ✅ | ✅ | ✅ | ✅ |
| Live Monitor (screen) | ✅ | ⚠️ | ⚠️ | ❌ | ⚠️ |
| Live Coach (real-time intervention) | ✅ | ✅ | ✅ | ✅ | ✅ |
| Review Queue | ✅ | ✅ | ✅ | ✅ | ✅ |
| Alerts + Acknowledgement | ✅ | ✅ | ✅ | ✅ | ✅ |
| Alert Explanations (LLM root cause) | ✅ | ❌ | — | ✅ | ✅ |
| Insights (rule-based) | ✅ | ✅ | ✅ | ✅ | ✅ |
| AI Narrative (NVIDIA NIM + Ollama fallback) | ✅ | ✅ | ✅ | ✅ | ✅ |
| AI Cost Tracking + Budget | ✅ | ❌ | — | ✅ | ✅ |
| Prompt Versioning + A/B | ✅ | ❌ | — | ✅ | ✅ |
| Compare Sessions | ✅ | ✅ | ✅ | ✅ | ✅ |
| Exports (PDF/Excel) | ✅ | ✅ | ✅ | ✅ | ✅ |
| Evidence Package (hash manifest + AI) | ✅ | ❌ | — | ✅ | ✅ |
| Profiles (OCR config) | ✅ | ✅ | ✅ | ✅ | ✅ |
| Clustering (HDBSCAN/cosine) | ✅ | ❌ | — | ✅ | ✅ |
| Dataset Quality Report | ✅ | ❌ | — | ✅ | ✅ |
| Event Validation (z-score) | ✅ | ❌ | — | ✅ | ✅ |
| Native Notifications (Tauri) | — | ✅ | ✅ | ❌ | ✅ |
| Sentry Crash Reporting | — | ✅ | ✅ | ❌ | ✅ |
| Portable Mode (--portable) | — | — | ✅ | ❌ | ✅ |
| Code Signing | — | — | ✅ | ❌ | ✅ |
| Auth (JWT + Refresh) | ✅ | ✅ | ⚠️ | ✅ | ⚠️ |
| Projects/Teams | ✅ | ❌ | ❌ | ❌ | ❌ |
| Jobs/Queue | ✅ | ✅ | ⚠️ | ✅ | ❌ |
| Admin Panel | ✅ | ✅ | ❌ | ❌ | ❌ |
| Parser Benchmark | ✅ | ✅ | ❌ | ❌ | ❌ |
| Auto-updater | ✅ | ❌ | ⚠️ | ❌ | ⚠️ |
| CI/CD (GitHub Actions) | ✅ | ✅ | ✅ | ✅ | ✅ |

**Legend**: ✅ Complete | ⚠️ Partial/WIP | ❌ Missing

---

## Documentation

| Document | Description |
|----------|-------------|
| [`10072026auditbytopencode.md`](10072026auditbytopencode.md) | **Deep codebase audit** — architecture, code quality, security, performance, 50 prioritized tasks |
| [`SessionGuardRevival.md`](SessionGuardRevival.md) | **6-phase execution handoff** (18 weeks) — tasks, owners, acceptance criteria, success metrics |

---

## Re-seed Demo Data

```bash
# Windows
scripts\seed_db.bat

# Mac/Linux
bash scripts/seed_db.sh
```

⚠ Deletes all data. Dev/testing only.

---

## What's Next — Roadmap to Production (v2.0)

See [`SessionGuardRevival.md`](SessionGuardRevival.md) for the detailed 18-week plan. High-level:

| Phase | Weeks | Focus | Status |
|-------|-------|-------|--------|
| 0 | — | Immediate hardening | ✅ Done (2026-07-21) |
| 1 | 1–3 | Foundations — Rate limiting, structured logging, secret management, DB indexes, React Query, route guards | ✅ Done |
| 2 | 4–6 | Hardening + FE Polish — Job workers, upload validation, test suite, API versioning, design tokens, Playwright E2E | ✅ Done |
| 3 | 7–9 | OCR/Video + Desktop Core — EasyOCR fallback, ROI auto-calibration, parallel OCR (8×), pHash dedup, auto-updater, system tray | ✅ Done (E1 Tauri v2 deferred) |
| 4 | 10–12 | AI Intelligence + Distribution — Structured AI outputs, prompt versioning, bundled deps, SQLCipher, event validation | ✅ Done (D2 pgvector deferred) |
| 5 | 13–15 | Advanced AI + Desktop Polish — Multi-region OCR, HDBSCAN, alert explanations, cost tracking, offline AI (Ollama), Coach, evidence packages, native notif, Sentry, portable mode, code signing, CI/CD | ✅ Done (2026-07-22) |
| 6 | 16–18 | SaaS Foundations + Launch — Multi-tenant (RLS), Stripe Billing, SSO/SCIM, audit export, public API, data residency, feature flags, SOC2 prep | ⚠️ Deferred (business-gated) |

**Target**: v1.5.0 — production local desktop app with signed installers, offline AI, evidence packages. Phase 6 (SaaS) requires committed business decision.

---

## License

Proprietary — SessionGuard Inc.
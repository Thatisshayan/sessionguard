# SessionGuard v1.2.0 — Local-First Session Intelligence Platform

Universal session intelligence for casino/slot analysis. Real OCR (Tesseract 5), behavior pattern detection (scikit-learn), live screen monitoring, video→event pipelines, AI narrative insights (Claude), multi-format exports. Desktop + Web.

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
| PySide6 | ✅ | Desktop shell (legacy) | Included in requirements.txt |
| EasyOCR (optional) | ➕ | GPU-accelerated OCR backup | `pip install easyocr` |
| PySide6-WebEngine | ➕ | Embed browser in desktop | `pip install PySide6-WebEngineWidgets` |

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
├── engines/                      # Core business logic (10 engines)
│   ├── analysis_engine.py        # Global KPIs, RTP distribution, net-over-time, by-game
│   ├── insights_engine.py        # Rule-based insight generation
│   ├── alerts_engine.py          # Threshold alerts — RTP, loss, streak
│   ├── review_queue_engine.py    # Uncertain-first queue
│   ├── comparison_engine.py      # Multi-session diff + narrative
│   ├── behavior_engine.py        # 5 sklearn patterns (tilt, drift, escalation, chasing, volatility)
│   ├── ocr_engine.py             # Tesseract 5 — ROI crop, preprocessing, field extraction
│   ├── video_pipeline.py         # FFmpeg → cv2 frames → OCR → events → review queue
│   ├── live_engine.py            # Mock + screen mode with thread lifecycle
│   ├── ai_insights_engine.py     # Claude Sonnet 4 narrative + risk scoring
│   └── cluster_engine.py         # Session similarity clustering
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

## API Reference (30+ Endpoints)

| Group | Key Endpoints |
|-------|---------------|
| Health | `GET /health`, `GET /health/detailed` |
| Auth | `POST /auth/login`, `POST /auth/signup`, `POST /auth/refresh`, `GET /auth/me` |
| Sessions | `GET/POST/PATCH/DELETE /sessions`, `GET /sessions/{id}`, `GET /sessions/{id}/ocr-results` |
| Metrics | `GET /metrics`, `/rtp-distribution`, `/net-over-time`, `/by-game`, `/session/{id}` |
| Insights | `GET /insights`, `POST /insights/{id}/regenerate` |
| Alerts | `GET /alerts`, `GET /alerts/summary`, `PATCH /alerts/{id}/acknowledge` |
| Review Queue | `GET /review-queue`, `GET /review-queue/summary`, `PATCH /review-queue/{id}/resolve` |
| Upload | `POST /upload`, `GET /upload`, `GET /upload/template/{type}` |
| Exports | `POST /exports`, `GET /exports`, `GET /exports/{id}/download` |
| Compare | `POST /compare` |
| Events | `GET /events`, `GET /events/summary`, `GET /events?session_id={id}` |
| Behavior | `GET /behavior/session/{id}`, `GET /behavior/global` |
| Live | `POST /live/start`, `POST /live/{id}/pause`, `POST /live/{id}/resume`, `POST /live/{id}/stop`, `GET /live/{id}/events` |
| Projects | `GET/POST/DELETE /projects` |
| Jobs | `GET/POST /jobs`, `GET /jobs/{id}`, `POST /jobs/{id}/cancel` |
| Admin | `GET /admin/system-health`, `GET /admin/system-stats`, `GET /admin/audit-log` |
| Intelligence | `POST /intelligence/clusters/build`, `GET /intelligence/clusters`, `GET /intelligence/anomalies` |
| AI Coach | `GET /intelligence/ai/status`, `GET /intelligence/ai/session/{id}`, `POST /intelligence/ai/compare` |
| OCR Calibrate | `POST /ocr/process`, `POST /ocr/calibrate`, `GET /ocr/status` |
| Updater | `GET /updater/check`, `GET /updater/current-version`, `POST /updater/dismiss` |
| Video Status | `GET /video-status`, `GET /ocr-status` |
| WebSocket | `WS /ws/connections` |

---

## Feature Completeness

| Feature | Backend | Frontend | Desktop | Tests | Docs |
|---------|---------|----------|---------|-------|------|
| Session CRUD | ✅ | ✅ | ✅ | ❌ | ✅ |
| CSV Upload (spin/session) | ✅ | ✅ | ✅ | ❌ | ✅ |
| OCR Engine (Tesseract) | ✅ | ✅ | ✅ | ❌ | ✅ |
| Video Pipeline | ✅ | ✅ | ⚠️ | ❌ | ✅ |
| Behavior Analysis (5 patterns) | ✅ | ✅ | ✅ | ❌ | ✅ |
| Live Monitor (mock) | ✅ | ✅ | ✅ | ❌ | ✅ |
| Live Monitor (screen) | ✅ | ⚠️ | ⚠️ | ❌ | ⚠️ |
| Review Queue | ✅ | ✅ | ✅ | ❌ | ✅ |
| Alerts + Acknowledgement | ✅ | ✅ | ✅ | ❌ | ✅ |
| Insights (rule-based) | ✅ | ✅ | ✅ | ❌ | ✅ |
| AI Narrative (Claude) | ✅ | ✅ | ✅ | ❌ | ✅ |
| Compare Sessions | ✅ | ✅ | ✅ | ❌ | ✅ |
| Exports (PDF/Excel) | ✅ | ✅ | ✅ | ❌ | ✅ |
| Profiles (OCR config) | ✅ | ✅ | ✅ | ❌ | ✅ |
| Auth (JWT + Refresh) | ✅ | ✅ | ⚠️ | ❌ | ⚠️ |
| Projects/Teams | ✅ | ❌ | ❌ | ❌ | ❌ |
| Jobs/Queue | ✅ | ✅ | ⚠️ | ❌ | ❌ |
| Admin Panel | ✅ | ✅ | ❌ | ❌ | ❌ |
| Parser Benchmark | ✅ | ✅ | ❌ | ❌ | ❌ |
| Auto-updater | ✅ | ❌ | ⚠️ | ❌ | ⚠️ |

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

| Phase | Weeks | Focus |
|-------|-------|-------|
| 1 | 1–3 | Foundations — PostgreSQL + Alembic, Redis registry, rate limiting, structured logging, secret management, DB indexes |
| 2 | 4–6 | Hardening + FE Polish — Celery workers, upload validation, test suite (80% coverage), API versioning, design tokens, React Query, Playwright E2E |
| 3 | 7–9 | OCR/Video + Desktop Core — EasyOCR fallback, ROI auto-calibration, parallel OCR (8×), Tauri v2 build, auto-updater, system tray |
| 4 | 10–12 | AI Intelligence + Distribution — Structured AI outputs, pgvector embeddings, prompt versioning, bundled deps, SQLCipher, code-sign |
| 5 | 13–15 | Advanced AI + Desktop Polish — Multi-region OCR, HDBSCAN clustering, alert explanations, cost tracking, offline AI, Coach, evidence packages |
| 6 | 16–18 | SaaS Foundations + Launch — Multi-tenant (RLS), Stripe Billing, SSO/SCIM, audit export, public API, data residency, feature flags, SOC2 prep |

**Target**: v2.0 — production SaaS + signed desktop installers + first paying customer.

---

## License

Proprietary — SessionGuard Inc.
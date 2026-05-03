# SessionGuard v0.5 — Phase 3 Complete

Universal session intelligence platform for casino/slot session analysis.
Local-first · Real OCR · Real Behavior Engine · Live Monitor · Full Exports.

---

## Quick Start

### 1. First-time setup

```
# Windows
scripts\setup.bat

# Mac / Linux
bash scripts/setup.sh
```

### 2. Start everything

```
# Windows
scripts\run_all.bat

# Mac / Linux
bash scripts/run_all.sh
```

### 3. Open

| Service     | URL                          |
|-------------|------------------------------|
| Dashboard   | http://localhost:5173        |
| API Docs    | http://127.0.0.1:8000/docs   |
| Desktop App | Launched by run_all          |

---

## Dependencies

| Dependency         | Required | Purpose                    | Install                                |
|--------------------|----------|----------------------------|----------------------------------------|
| Python 3.11+       | ✅        | Backend + engines          | https://python.org                     |
| Node.js 18+        | ✅        | React frontend             | https://nodejs.org                     |
| FFmpeg             | ✅ Video  | Frame extraction           | https://ffmpeg.org/download.html       |
| Tesseract 5        | ✅ OCR    | Field extraction from frames | https://github.com/tesseract-ocr      |
| PySide6            | ✅        | Desktop shell              | Included in requirements.txt           |
| EasyOCR (optional) | ➕        | GPU-accelerated OCR backup | pip install easyocr                    |
| PySide6-WebEngine  | ➕        | Embed browser in desktop   | pip install PySide6-WebEngineWidgets   |

---

## Architecture

```
sessionguard/
  backend/
    main.py              FastAPI app factory — 15 route groups registered
    routes/              One file per endpoint group (health, sessions, metrics,
                         insights, alerts, review_queue, uploads, exports, compare,
                         profiles, video_status, ocr_status, events, behavior, live)
    services/
      csv_parser.py      Auto-detect spin-level / session-level CSV, parse to events
      export_service.py  PDF (ReportLab 4.x charts) + Excel (openpyxl multi-sheet)
  engines/
    analysis_engine.py   Global metrics, RTP distribution, net over time, by-game
    insights_engine.py   Rule-based insight generation per session
    alerts_engine.py     Threshold alerts — RTP, loss, streak
    review_queue_engine  Uncertain-first queue — accept/reject/correct
    comparison_engine.py Multi-session diff with narrative
    behavior_engine.py   sklearn — bet escalation, tilt, drift, chasing, volatility
    ocr_engine.py        Tesseract 5 — ROI crop, preprocessing, field extraction
    video_pipeline.py    cv2 frame extraction + OCR pass + event building
    live_engine.py       Real-time mock + screen session monitoring with threads
  frontend/
    src/pages/
      Dashboard.tsx      KPIs + charts + behavior risk banner + insights + alerts
      Sessions.tsx        List with filters, sorting, click-through to detail
      SessionDetail.tsx   Event timeline + behavior + review queue + exports
      Compare.tsx         Radar chart + metric breakdown + narrative
      LiveMonitor.tsx     Real-time event feed + chart + controls
      Upload.tsx          Drag-drop + CSV template download + status polling
      ReviewQueue.tsx     Uncertain-first + accept/reject/correct
      Reports.tsx         All four export formats + history
      Profiles.tsx        Per-game OCR config + alert thresholds
      Settings.tsx        Dependency status + engine status + version info
  desktop_app/
    app/main.py          PySide6 entry point
    app/window.py        Tabbed shell — embedded browser + service controls + deps
    recorder/            FFmpeg runner (wired for V8 screen recording)
  database/
    db.py               14-table SQLite schema + casino/slot seeder
  config/
    app_config.json     Runtime config
    profiles/           Per-game OCR profiles
  scripts/              .bat + .sh for setup, run_all, each service, seed_db
```

---

## API Reference (30+ endpoints)

| Group         | Key Endpoints                                           |
|---------------|---------------------------------------------------------|
| Health        | GET /health                                             |
| Sessions      | GET/POST/PATCH/DELETE /sessions, GET /sessions/{id}     |
| Metrics       | GET /metrics, /metrics/rtp-distribution, /by-game       |
| Insights      | GET /insights, POST /insights/{id}/regenerate           |
| Alerts        | GET /alerts, PATCH /alerts/{id}/acknowledge             |
| Review Queue  | GET /review-queue, PATCH /review-queue/{id}/resolve     |
| Upload        | POST /upload, GET /upload, GET /upload/template/{type}  |
| Exports       | POST /exports, GET /exports/{id}/download               |
| Compare       | POST /compare                                           |
| Events (P3)   | GET /events, GET /events/summary                        |
| Behavior (P3) | GET /behavior/session/{id}, GET /behavior/global         |
| Live (P3)     | POST /live/start, /pause, /resume, /stop, /events        |
| Video         | GET /video-status, /ocr-status                          |

---

## QA Acceptance Checklist

- [ ] `GET /health` returns 200
- [ ] Dashboard loads with real KPIs
- [ ] Sessions list shows 12+ sessions
- [ ] Click a session → SessionDetail shows real event timeline chart
- [ ] Behavior tab shows risk analysis
- [ ] Upload CSV (spin-level) → session + events created automatically
- [ ] Upload CSV (session-level) → sessions created automatically
- [ ] PDF export → real file with charts and event log
- [ ] Excel export → multi-sheet styled workbook
- [ ] Live Monitor → Start → events stream in → Pause → Resume → Stop
- [ ] Review queue actions persist (accept/reject/correct)
- [ ] Alert acknowledgement removes from dashboard
- [ ] Settings shows all dependency status
- [ ] Scripts work with spaces in path on Windows

---

## Phase 3 What's New vs Phase 2

| Feature                 | Phase 2 | Phase 3 |
|-------------------------|---------|---------|
| OCR engine              | Scaffold | ✅ Real Tesseract 5 + field extraction |
| Video pipeline          | FFmpeg check | ✅ cv2 frame extraction + OCR pass + events |
| Behavior engine         | Scaffold | ✅ 5 sklearn patterns (tilt, drift, escalation…) |
| Live Monitor            | None | ✅ Mock + screen mode, pause/resume/stop |
| Events endpoint         | None | ✅ Real timeline with cumulative net |
| Session event chart     | Simulated | ✅ Real balance curve from events |
| Win distribution chart  | None | ✅ Bucketed bar chart |
| Behavior tab            | None | ✅ Per-session risk score + pattern cards |
| Export download button  | None | ✅ /exports/{id}/download → file |
| Desktop embedded browser| None | ✅ QWebEngineView (if installed) |
| DB tables               | 9 | 14 (live_runs, live_events, ocr_results, video_jobs…) |
| Backend routes          | 12 | 15 (+events, +behavior, +live) |

---

## What's Next — Phase 4 (V6)

- Auth layer (JWT, hashed passwords, user model)
- PostgreSQL migration (Alembic migrations, asyncpg)
- Cloud sync architecture
- Real screen-mode OCR calibration UI
- Tauri native desktop build (source already in desktop_shell/)
- PDF letterhead polish + evidence package builder
- EasyOCR GPU fallback
- Parser benchmark screen

---

## Re-seed Demo Data

```
# Windows
scripts\seed_db.bat

# Mac/Linux
bash scripts/seed_db.sh
```

⚠ Deletes all data. Dev/testing only.

"""backend/main.py -- SessionGuard v1.2.0"""
import os, sys, platform
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path: sys.path.insert(0, str(ROOT))

# ── Windows: pin Tesseract paths before any engine imports pytesseract ────────
if platform.system() == "Windows":
    _tess_data = r"C:\Program Files\Tesseract-OCR\tessdata"
    _tess_exe  = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
    if Path(_tess_data).exists():
        os.environ["TESSDATA_PREFIX"] = _tess_data
    try:
        import pytesseract
        if Path(_tess_exe).exists():
            pytesseract.pytesseract.tesseract_cmd = _tess_exe
    except ImportError:
        pass

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from database.db import init_db, init_db_v2, init_db_v3, init_db_v4, init_db_v5, seed_demo_data, seed_demo_user
from engines.alert_presets import seed_presets
from backend.routes import (
    health, sessions, metrics, insights, alerts,
    review_queue, uploads, exports, compare, profiles,
    video_status, ocr_status, events, behavior, live,
    auth, projects, jobs, admin, parser_benchmark,
    ws, notes, evidence, recorder, openapi_export,
    system_config, data_export, trends, search,
    tags, intelligence, coach, ocr_calibrate, updater, import_wizard,
)

app = FastAPI(title="SessionGuard API", version="1.2.0", docs_url="/docs")

ORIGINS = ["http://localhost:5173","http://127.0.0.1:5173","http://localhost:3000",
           "http://127.0.0.1:3000","http://localhost:1420","http://127.0.0.1:1420"]
extra = os.getenv("CORS_ORIGINS","")
if extra: ORIGINS += [o.strip() for o in extra.split(",") if o.strip()]

app.add_middleware(CORSMiddleware, allow_origins=ORIGINS, allow_credentials=True,
                   allow_methods=["*"], allow_headers=["*"])

@app.on_event("startup")
def on_startup():
    init_db(); init_db_v2(); init_db_v3(); init_db_v4(); init_db_v5()
    seed_demo_data(); seed_demo_user(); seed_presets()

    # Load API key from environment (secure method)
    api_key = os.getenv("ANTHROPIC_API_KEY", "").strip()
    if api_key:
        os.environ["ANTHROPIC_API_KEY"] = api_key

    print("[API] SessionGuard v1.2.0 ready -> http://127.0.0.1:8000")
    print("[API] Login -> demo@sessionguard.local / demo123")
    print("[API] Coach -> /coach-status | Updater -> /updater/check")

app.include_router(health.router)
app.include_router(sessions.router,          prefix="/sessions")
app.include_router(metrics.router,           prefix="/metrics")
app.include_router(insights.router,          prefix="/insights")
app.include_router(alerts.router,            prefix="/alerts")
app.include_router(review_queue.router,      prefix="/review-queue")
app.include_router(uploads.router,           prefix="/upload")
app.include_router(exports.router,           prefix="/exports")
app.include_router(compare.router,           prefix="/compare")
app.include_router(profiles.router,          prefix="/profiles")
app.include_router(video_status.router,      prefix="/video-status")
app.include_router(ocr_status.router,        prefix="/ocr-status")
app.include_router(events.router,            prefix="/events")
app.include_router(behavior.router,          prefix="/behavior")
app.include_router(live.router,              prefix="/live")
app.include_router(auth.router,              prefix="/auth")
app.include_router(projects.router,          prefix="/projects")
app.include_router(jobs.router,              prefix="/jobs")
app.include_router(admin.router,             prefix="/admin")
app.include_router(parser_benchmark.router,  prefix="/parser-benchmark")
app.include_router(ws.router)
app.include_router(notes.router,             prefix="/sessions")
app.include_router(evidence.router,          prefix="/sessions")
app.include_router(recorder.router)
app.include_router(openapi_export.router)
app.include_router(system_config.router)
app.include_router(data_export.router)
app.include_router(trends.router)
app.include_router(search.router)
app.include_router(tags.router)
app.include_router(intelligence.router)
app.include_router(coach.router)
app.include_router(ocr_calibrate.router)
app.include_router(updater.router)
app.include_router(import_wizard.router)


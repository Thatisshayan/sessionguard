"""backend/main.py -- SessionGuard API"""
import os, sys, platform
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path: sys.path.insert(0, str(ROOT))

# ── Load .env file if present (before any env var reads) ──────────────────────
try:
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
except ImportError:
    pass

def _configure_windows_tesseract():
    """Prefer explicit/bundled Tesseract paths before falling back to system install."""
    if platform.system() != "Windows":
        return

    bundled_root = ROOT / "tesseract_win"
    tess_exe = os.getenv("SESSIONGUARD_TESSERACT_CMD")
    tess_data = os.getenv("TESSDATA_PREFIX")

    if not tess_exe:
        bundled_exe = bundled_root / "tesseract.exe"
        system_exe = Path(r"C:\Program Files\Tesseract-OCR\tesseract.exe")
        if bundled_exe.exists():
            tess_exe = str(bundled_exe)
        elif system_exe.exists():
            tess_exe = str(system_exe)

    if not tess_data:
        bundled_data = bundled_root / "tessdata"
        system_data = Path(r"C:\Program Files\Tesseract-OCR\tessdata")
        if bundled_data.exists():
            tess_data = str(bundled_data)
        elif system_data.exists():
            tess_data = str(system_data)

    if tess_data:
        os.environ["TESSDATA_PREFIX"] = tess_data

    try:
        import pytesseract
        if tess_exe and Path(tess_exe).exists():
            pytesseract.pytesseract.tesseract_cmd = tess_exe
    except ImportError:
        pass


_configure_windows_tesseract()

# ── Optional Sentry crash reporting ─────────────────────────────────────────
sentry_dsn = os.getenv("SENTRY_DSN")
if sentry_dsn:
    try:
        import sentry_sdk
        sentry_sdk.init(dsn=sentry_dsn, traces_sample_rate=0.2)
    except ImportError:
        pass

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from backend.version import APP_VERSION
from database.db import init_db, init_db_v2, init_db_v3, init_db_v4, init_db_v5, init_db_v6, init_db_v7, init_db_v8, init_db_v9, init_db_v10, init_db_v11, init_db_v12, init_db_v13, init_db_v14, init_db_v15, seed_demo_data, seed_demo_user
from backend.auth.service import get_current_user_from_token
from engines.alert_presets import seed_presets
from backend.middleware.logging import configure_logging, RequestLoggingMiddleware

configure_logging()
from backend.routes import (
    health, sessions, metrics, insights, alerts,
    review_queue, uploads, exports, compare, profiles,
    video_status, ocr_status, events, behavior, live,
    auth, projects, jobs, admin, parser_benchmark,
    ws, notes, evidence, recorder, openapi_export,
    system_config, data_export, trends, search,
    tags, intelligence, coach, ocr_calibrate, updater, import_wizard,
    dashboard, video_jobs, prompts, dataset_quality, ai_analysis,
)

app = FastAPI(title="SessionGuard API", version=APP_VERSION, docs_url="/docs")
app.add_middleware(GZipMiddleware, minimum_size=1000)

ORIGINS = ["http://localhost:5173","http://127.0.0.1:5173","http://localhost:3000",
           "http://127.0.0.1:3000","http://localhost:1420","http://127.0.0.1:1420"]
extra = os.getenv("CORS_ORIGINS","")
if extra: ORIGINS += [o.strip() for o in extra.split(",") if o.strip()]

app.add_middleware(CORSMiddleware, allow_origins=ORIGINS, allow_credentials=True,
                   allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
                   allow_headers=["Content-Type", "Authorization", "X-Requested-With"])
app.add_middleware(RequestLoggingMiddleware)

@app.middleware("http")
async def require_authenticated_api(request: Request, call_next):
    path = request.url.path
    if request.method == "OPTIONS" or not path.startswith("/api/v1/"):
        return await call_next(request)
    public_prefixes = (
        "/api/v1/auth",
        "/api/v1/health",
    )
    if path.startswith(public_prefixes):
        return await call_next(request)

    current_user = get_current_user_from_token(request.headers.get("authorization"))
    if not current_user:
        return JSONResponse(status_code=401, content={"detail": "Authentication required."})

    request.state.current_user = current_user
    return await call_next(request)

@app.on_event("startup")
def on_startup():
    init_db(); init_db_v2(); init_db_v3(); init_db_v4(); init_db_v5(); init_db_v6(); init_db_v7(); init_db_v8()
    init_db_v9(); init_db_v10(); init_db_v11()
    seed_demo_user()
    init_db_v12(); init_db_v13(); init_db_v14(); init_db_v15()
    seed_demo_data(); seed_presets()

    # Load API key from environment (secure method)
    api_key = os.getenv("NVIDIA_API_KEY", "").strip()
    if api_key:
        os.environ["NVIDIA_API_KEY"] = api_key

    print(f"[API] SessionGuard v{APP_VERSION} ready -> http://127.0.0.1:8000")
    print("[API] Coach -> /coach-status | Updater -> /updater/check")

app.include_router(health.router)  # Unversioned
app.include_router(sessions.router,          prefix="/api/v1/sessions")
app.include_router(metrics.router,           prefix="/api/v1/metrics")
app.include_router(insights.router,          prefix="/api/v1/insights")
app.include_router(alerts.router,            prefix="/api/v1/alerts")
app.include_router(review_queue.router,      prefix="/api/v1/review-queue")
app.include_router(uploads.router,           prefix="/api/v1/upload")
app.include_router(exports.router,           prefix="/api/v1/exports")
app.include_router(compare.router,           prefix="/api/v1/compare")
app.include_router(profiles.router,          prefix="/api/v1/profiles")
app.include_router(video_status.router,      prefix="/api/v1/video-status")
app.include_router(ocr_status.router,        prefix="/api/v1/ocr-status")
app.include_router(events.router,            prefix="/api/v1/events")
app.include_router(behavior.router,          prefix="/api/v1/behavior")
app.include_router(live.router,              prefix="/api/v1/live")
app.include_router(auth.router,              prefix="/api/v1/auth")
app.include_router(projects.router,          prefix="/api/v1/projects")
app.include_router(jobs.router,              prefix="/api/v1/jobs")
app.include_router(admin.router,             prefix="/api/v1/admin")
app.include_router(parser_benchmark.router,  prefix="/api/v1/parser-benchmark")
app.include_router(ws.router,               prefix="/api/v1/ws")
app.include_router(notes.router,             prefix="/api/v1/sessions")
app.include_router(evidence.router,          prefix="/api/v1/sessions")
app.include_router(recorder.router,          prefix="/api/v1/recorder")
app.include_router(openapi_export.router,    prefix="/api/v1/openapi-export")
app.include_router(system_config.router,     prefix="/api/v1/system-config")
app.include_router(data_export.router,       prefix="/api/v1/data-export")
app.include_router(trends.router,           prefix="/api/v1/trends")
app.include_router(search.router,           prefix="/api/v1/search")
app.include_router(tags.router,             prefix="/api/v1/tags")
app.include_router(intelligence.router,     prefix="/api/v1/intelligence")
app.include_router(coach.router,            prefix="/api/v1/coach")
app.include_router(ocr_calibrate.router,    prefix="/api/v1/ocr-calibrate")
app.include_router(updater.router,          prefix="/api/v1/updater")
app.include_router(import_wizard.router,     prefix="/api/v1/import-wizard")
app.include_router(dashboard.router,        prefix="/api/v1/dashboard")
app.include_router(video_jobs.router,       prefix="/api/v1/video-jobs")
app.include_router(prompts.router,          prefix="/api/v1/prompts")
app.include_router(dataset_quality.router, prefix="/api/v1/intelligence/dataset-quality")
app.include_router(ai_analysis.router,      prefix="/api/v1")


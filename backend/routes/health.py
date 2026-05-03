"""
backend/routes/health.py — Basic + detailed health checks.
"""

from fastapi import APIRouter
from datetime import datetime, timezone

router = APIRouter(tags=["health"])


@router.get("/health")
def health_check():
    return {
        "status":    "ok",
        "service":   "SessionGuard API",
        "version":   "0.6.0",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/health/detailed")
def health_detailed():
    """Full system health — DB, FFmpeg, Tesseract, all engines."""
    import shutil, subprocess
    from database.db import get_connection

    result = {
        "status":    "ok",
        "version":   "0.6.0",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "checks":    {},
    }

    # DB
    try:
        conn     = get_connection()
        tables   = conn.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'").fetchone()[0]
        sessions = conn.execute("SELECT COUNT(*) FROM sessions").fetchone()[0]
        conn.close()
        result["checks"]["database"] = {"ok": True, "tables": tables, "sessions": sessions}
    except Exception as e:
        result["checks"]["database"] = {"ok": False, "error": str(e)}
        result["status"] = "degraded"

    # FFmpeg
    ff_path = shutil.which("ffmpeg")
    result["checks"]["ffmpeg"] = {"ok": bool(ff_path), "path": ff_path}
    if not ff_path:
        result["status"] = "degraded"

    # Tesseract
    tess_path = shutil.which("tesseract")
    if tess_path:
        try:
            r = subprocess.run(["tesseract","--version"], capture_output=True, text=True, timeout=3)
            ver = r.stdout.splitlines()[0] if r.stdout else r.stderr.splitlines()[0]
        except Exception:
            ver = "unknown"
    else:
        ver = None
    result["checks"]["tesseract"] = {"ok": bool(tess_path), "version": ver}

    # All 10 engines
    engine_results = {}
    for mod in ["analysis_engine","insights_engine","alerts_engine","review_queue_engine",
                "comparison_engine","behavior_engine","ocr_engine","video_pipeline",
                "live_engine","parser_benchmark"]:
        try:
            __import__(f"engines.{mod}")
            engine_results[mod] = True
        except Exception as e:
            engine_results[mod] = str(e)[:60]
    result["checks"]["engines"] = {
        "ok":      all(v is True for v in engine_results.values()),
        "results": engine_results,
    }

    # WebSocket manager
    try:
        from backend.routes.ws import manager
        result["checks"]["websocket"] = {"ok": True, "connections": manager.connection_count()}
    except Exception:
        result["checks"]["websocket"] = {"ok": False}

    return result

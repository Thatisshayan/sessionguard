"""
desktop_app/recorder/ffmpeg_runner.py
--------------------------------------
Real FFmpeg-based screen recorder. Cross-platform.
Start/stop recording sessions, link to live session IDs.

Maturity: Working Prototype
Future:   Game-window targeting (V9), multi-monitor (V10).
"""

from __future__ import annotations
import os, shutil, subprocess, sys, threading, time
from datetime import datetime
from pathlib import Path
from typing import Optional

BASE_DIR   = Path(__file__).resolve().parent.parent.parent
RECORDINGS = BASE_DIR / "storage" / "recordings"
RECORDINGS.mkdir(parents=True, exist_ok=True)


def _platform() -> str:
    if sys.platform.startswith("win"): return "windows"
    if sys.platform == "darwin":       return "macos"
    return "linux"


def _input_args(platform: str, fps: int, region: Optional[tuple]) -> list[str]:
    if platform == "windows":
        args = ["-f", "gdigrab", "-framerate", str(fps)]
        if region:
            x, y, w, h = region
            args += ["-offset_x", str(x), "-offset_y", str(y), "-video_size", f"{w}x{h}"]
        return args + ["-i", "desktop"]
    if platform == "macos":
        return ["-f", "avfoundation", "-framerate", str(fps), "-i", "1:none"]
    # Linux X11
    display = os.environ.get("DISPLAY", ":0")
    args = ["-f", "x11grab", "-framerate", str(fps)]
    if region:
        x, y, w, h = region
        args += ["-video_size", f"{w}x{h}", "-i", f"{display}+{x},{y}"]
    else:
        args += ["-i", display]
    return args


class ScreenRecorder:
    def __init__(self, output_path: str, fps: int = 30,
                 region: Optional[tuple] = None):
        self.output_path  = Path(output_path)
        self.fps          = fps
        self.region       = region
        self._platform    = _platform()
        self._process: Optional[subprocess.Popen] = None
        self._lock        = threading.Lock()
        self._started_at: Optional[float]         = None
        self.error: Optional[str]                 = None

    @property
    def is_recording(self) -> bool:
        with self._lock:
            return self._process is not None and self._process.poll() is None

    @property
    def duration(self) -> float:
        return round(time.monotonic() - self._started_at, 1) if self._started_at else 0.0

    def start(self) -> dict:
        if not shutil.which("ffmpeg"):
            return {"success": False, "error": "FFmpeg not found on PATH."}
        if self.is_recording:
            return {"success": False, "error": "Already recording."}
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        self.error = None
        cmd = (["ffmpeg", "-y"]
               + _input_args(self._platform, self.fps, self.region)
               + ["-c:v", "libx264", "-preset", "ultrafast",
                  "-crf", "28", "-pix_fmt", "yuv420p",
                  str(self.output_path)])
        try:
            with self._lock:
                self._process    = subprocess.Popen(cmd, stdin=subprocess.PIPE,
                                                     stdout=subprocess.DEVNULL,
                                                     stderr=subprocess.PIPE)
                self._started_at = time.monotonic()
            return {"success": True, "output_path": str(self.output_path),
                    "platform": self._platform}
        except Exception as e:
            self.error = str(e)
            return {"success": False, "error": str(e)}

    def stop(self) -> dict:
        with self._lock:
            proc = self._process
        if proc is None or proc.poll() is not None:
            return {"success": False, "error": "Not recording."}
        try:
            proc.stdin.write(b"q"); proc.stdin.flush(); proc.wait(timeout=10)
        except Exception:
            proc.terminate(); proc.wait(timeout=5)
        dur  = self.duration
        size = self.output_path.stat().st_size if self.output_path.exists() else 0
        with self._lock:
            self._process    = None
            self._started_at = None
        return {"success": True, "output_path": str(self.output_path),
                "duration_s": dur, "size_bytes": size}

    def status(self) -> dict:
        return {"recording": self.is_recording, "duration_s": self.duration,
                "output_path": str(self.output_path), "error": self.error}


# ── Global instance ───────────────────────────────────────────────────────────
_active: Optional[ScreenRecorder] = None
_lock   = threading.Lock()


def start_recording(session_id: Optional[int] = None, fps: int = 30,
                    region: Optional[tuple] = None) -> dict:
    global _active
    with _lock:
        if _active and _active.is_recording:
            return {"success": False, "error": "Already recording."}
        ts     = datetime.now().strftime("%Y%m%d_%H%M%S")
        label  = f"session_{session_id}_" if session_id else ""
        path   = RECORDINGS / f"recording_{label}{ts}.mp4"
        _active = ScreenRecorder(str(path), fps=fps, region=region)
        result  = _active.start()
        result["session_id"] = session_id
        return result


def stop_recording() -> dict:
    global _active
    with _lock:
        if not _active or not _active.is_recording:
            return {"success": False, "error": "Not recording."}
        return _active.stop()


def get_recording_status() -> dict:
    global _active
    with _lock:
        if not _active:
            return {"recording": False, "duration_s": 0, "error": None}
        return _active.status()


def list_recordings() -> list[dict]:
    return [
        {"filename": f.name, "path": str(f),
         "size_bytes": f.stat().st_size,
         "created": datetime.fromtimestamp(f.stat().st_ctime).isoformat()}
        for f in sorted(RECORDINGS.glob("*.mp4"))
    ]

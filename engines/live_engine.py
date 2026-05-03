"""
engines/live_engine.py
-----------------------
Real live session monitoring engine.
Adapted from the project source live_engine.py with DB integration.

Modes:
  mock   — generates realistic synthetic events (no screen access needed)
  screen — captures screen, runs OCR, extracts real events

Thread lifecycle: start → running ↔ paused → stopped
Autosave: checkpoints every N ticks to survive crashes.

Maturity: Working Prototype — mock mode fully working.
          Screen mode: capture + OCR real, but ROI calibration is manual.
Future:   Auto-ROI detection (V8), multi-monitor (V9).
"""

from __future__ import annotations
import json
import random
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Callable, Optional

from database.db import get_connection

BASE_DIR  = Path(__file__).resolve().parent.parent
LIVE_DIR  = BASE_DIR / "storage" / "recordings" / "live"
LIVE_DIR.mkdir(parents=True, exist_ok=True)

# ── In-memory run registry (cleared on server restart) ────────────────────────
_ACTIVE_RUNS: dict[int, "LiveRunThread"] = {}


# ── Mock event generator ──────────────────────────────────────────────────────

def _mock_event(event_index: int, session_meta: dict) -> dict:
    """Generate a realistic synthetic spin event."""
    avg_bet     = session_meta.get("avg_bet", 1.0)
    bet         = round(avg_bet * random.uniform(0.5, 2.0), 2)
    roll        = random.random()
    win         = 0.0
    if roll < 0.45:
        win = 0.0
    elif roll < 0.75:
        win = round(bet * random.uniform(0.5, 2.0), 2)
    elif roll < 0.95:
        win = round(bet * random.uniform(2.0, 10.0), 2)
    else:
        win = round(bet * random.uniform(10.0, 50.0), 2)

    confidence  = round(random.uniform(0.65, 0.99), 2)
    scene_score = round(random.uniform(5.0, 35.0), 2)

    return {
        "event_index": event_index,
        "tick_label":  f"spin-{event_index}",
        "bet_amount":  bet,
        "win_amount":  win,
        "net_delta":   round(win - bet, 2),
        "ocr_confidence": confidence,
        "scene_score": scene_score,
        "risk_flag":   scene_score > 24 or confidence < 0.75,
        "event_type":  "spin",
    }


def _screen_event(event_index: int, frame_path: str, roi_config: dict | None) -> dict:
    """Capture screen, run OCR, return structured event payload."""
    try:
        from PIL import ImageGrab
        from engines.ocr_engine import extract_fields_from_image

        img = ImageGrab.grab(all_screens=True)
        Path(frame_path).parent.mkdir(parents=True, exist_ok=True)
        img.save(frame_path)

        fields = extract_fields_from_image(frame_path, roi_config=roi_config)
        f      = fields.get("fields", {})

        return {
            "event_index":    event_index,
            "event_type":     "screen_tick",
            "frame_path":     frame_path,
            "balance":        f.get("balance", {}).get("value"),
            "bet_amount":     f.get("bet",     {}).get("value") or 0,
            "win_amount":     f.get("win",     {}).get("value") or 0,
            "ocr_confidence": fields.get("overall_confidence", 0),
            "risk_flag":      fields.get("flagged", False),
        }
    except Exception as e:
        return {
            "event_index":  event_index,
            "event_type":   "screen_error",
            "error":        str(e),
            "risk_flag":    True,
        }


# ── DB writers ────────────────────────────────────────────────────────────────

def _write_event(run_id: int, session_id: int, event_type: str, payload: dict):
    conn = get_connection()
    conn.execute(
        "INSERT INTO live_events (run_id, session_id, event_type, payload) VALUES (?,?,?,?)",
        (run_id, session_id, event_type, json.dumps(payload))
    )
    conn.commit()
    conn.close()


def _write_checkpoint(run_id: int, session_id: int, data: dict):
    conn = get_connection()
    conn.execute(
        "INSERT INTO live_checkpoints (run_id, session_id, data) VALUES (?,?,?)",
        (run_id, session_id, json.dumps(data))
    )
    conn.commit()
    conn.close()


def _write_status(run_id: int, status: str, event_index: int):
    conn = get_connection()
    extra = ", stopped_at=datetime('now')" if status == "stopped" else ""
    conn.execute(
        f"UPDATE live_runs SET status=?, event_index=? {extra} WHERE id=?",
        (status, event_index, run_id)
    )
    conn.commit()
    conn.close()


# ── Thread ────────────────────────────────────────────────────────────────────

class LiveRunThread(threading.Thread):
    """
    Background thread that drives a live session tick loop.
    Each tick: capture/generate event → persist → checkpoint if due.
    """

    def __init__(
        self,
        run_id: int,
        session_id: int,
        mode: str,
        start_index: int,
        tick_interval: float,
        autosave_enabled: bool,
        session_meta: dict | None = None,
        roi_config: dict | None   = None,
    ):
        super().__init__(daemon=True)
        self.run_id           = run_id
        self.session_id       = session_id
        self.mode             = mode
        self.event_index      = start_index
        self.tick_interval    = tick_interval
        self.autosave_enabled = autosave_enabled
        self.session_meta     = session_meta or {}
        self.roi_config       = roi_config

        self._stop_event   = threading.Event()
        self._pause_event  = threading.Event()

    def pause(self):
        self._pause_event.set()

    def resume(self):
        self._pause_event.clear()

    def stop(self):
        self._stop_event.set()

    def run(self):
        _write_status(self.run_id, "running", self.event_index)
        live_dir = LIVE_DIR / f"run_{self.run_id}"
        live_dir.mkdir(parents=True, exist_ok=True)

        while not self._stop_event.is_set():
            if self._pause_event.is_set():
                _write_status(self.run_id, "paused", self.event_index)
                time.sleep(0.3)
                continue

            self.event_index += 1

            if self.mode == "screen":
                frame_path = str(live_dir / f"frame_{self.event_index:04d}.png")
                payload    = _screen_event(self.event_index, frame_path, self.roi_config)
            else:
                payload = _mock_event(self.event_index, self.session_meta)

            _write_event(self.run_id, self.session_id, payload["event_type"], payload)

            # Autosave checkpoint every 5 ticks
            if self.autosave_enabled and self.event_index % 5 == 0:
                _write_checkpoint(self.run_id, self.session_id, {
                    "last_event_index": self.event_index,
                    "mode":             self.mode,
                    "status":           "running",
                    "timestamp":        datetime.now().isoformat(),
                })

            _write_status(self.run_id, "running", self.event_index)
            time.sleep(self.tick_interval)

        _write_status(self.run_id, "stopped", self.event_index)


# ── Public API ────────────────────────────────────────────────────────────────

def start_live_run(
    session_id: int,
    mode: str = "mock",
    tick_interval: float = 2.0,
    autosave_enabled: bool = True,
    roi_config: dict | None = None,
) -> dict:
    """
    Create a live_runs record and start the background thread.
    Returns run metadata.
    """
    conn = get_connection()

    # Fetch session meta for mock event generator
    s = conn.execute("SELECT * FROM sessions WHERE id=?", (session_id,)).fetchone()
    if not s:
        conn.close()
        return {"success": False, "error": f"Session {session_id} not found."}

    session_meta = {
        "avg_bet": round(
            (s["total_bets"] or 10) / max(s["spins"] or 1, 1), 2
        ),
        "game_name": s["game_name"],
    }

    # Check for existing running run for this session
    existing = conn.execute(
        "SELECT id FROM live_runs WHERE session_id=? AND status='running'",
        (session_id,)
    ).fetchone()
    if existing:
        conn.close()
        return {"success": False, "error": f"Session {session_id} already has a running live session (run #{existing['id']})."}

    # Check for resumable checkpoint
    last_run = conn.execute(
        "SELECT * FROM live_runs WHERE session_id=? ORDER BY id DESC LIMIT 1",
        (session_id,)
    ).fetchone()
    start_index = 0
    if last_run and last_run["status"] in ("stopped", "paused"):
        start_index = last_run["event_index"]

    cur = conn.execute(
        """INSERT INTO live_runs
           (session_id, mode, status, event_index, tick_interval, autosave_enabled, metadata)
           VALUES (?,?,'running',?,?,?,?)""",
        (session_id, mode, start_index, tick_interval,
         int(autosave_enabled), json.dumps(roi_config or {}))
    )
    run_id = cur.lastrowid
    conn.commit()
    conn.close()

    thread = LiveRunThread(
        run_id=run_id,
        session_id=session_id,
        mode=mode,
        start_index=start_index,
        tick_interval=tick_interval,
        autosave_enabled=autosave_enabled,
        session_meta=session_meta,
        roi_config=roi_config,
    )
    thread.start()
    _ACTIVE_RUNS[run_id] = thread

    return {
        "success": True,
        "run_id":  run_id,
        "mode":    mode,
        "session_id": session_id,
        "resumed_from_index": start_index,
    }


def pause_live_run(run_id: int) -> dict:
    thread = _ACTIVE_RUNS.get(run_id)
    if not thread or not thread.is_alive():
        return {"success": False, "error": f"Run {run_id} is not active."}
    thread.pause()
    return {"success": True, "run_id": run_id, "status": "paused"}


def resume_live_run(run_id: int) -> dict:
    thread = _ACTIVE_RUNS.get(run_id)
    if not thread or not thread.is_alive():
        return {"success": False, "error": f"Run {run_id} is not active."}
    thread.resume()
    return {"success": True, "run_id": run_id, "status": "running"}


def stop_live_run(run_id: int) -> dict:
    thread = _ACTIVE_RUNS.pop(run_id, None)
    if thread:
        thread.stop()
        thread.join(timeout=5)
    _write_status(run_id, "stopped", _get_run_event_index(run_id))
    return {"success": True, "run_id": run_id, "status": "stopped"}


def _get_run_event_index(run_id: int) -> int:
    conn = get_connection()
    row  = conn.execute("SELECT event_index FROM live_runs WHERE id=?", (run_id,)).fetchone()
    conn.close()
    return row["event_index"] if row else 0


def get_live_run(run_id: int) -> dict | None:
    conn = get_connection()
    row  = conn.execute("SELECT * FROM live_runs WHERE id=?", (run_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def get_live_events(run_id: int, since_id: int = 0, limit: int = 50) -> list[dict]:
    """Return live events for a run, optionally since a given event ID (for polling)."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM live_events WHERE run_id=? AND id>? ORDER BY id DESC LIMIT ?",
        (run_id, since_id, limit)
    ).fetchall()
    conn.close()
    result = []
    for r in rows:
        d = dict(r)
        try:
            d["payload"] = json.loads(d["payload"])
        except Exception:
            pass
        result.append(d)
    return list(reversed(result))


def get_session_live_runs(session_id: int) -> list[dict]:
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM live_runs WHERE session_id=? ORDER BY id DESC",
        (session_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]

"""Runner-free regression for the bundled-backend smoke (Revival 1.3, A1).

The desktop installer silently running stale backend code was finding #13 in
``SESSIONGUARDREVIVAL1.3.md``. ``.github/workflows/bundled-backend-smoke.yml``
guards this on GitHub runners; this test reproduces the same contract locally
so the regression is caught without waiting for CI:

  1. run ``desktop_shell/stage-backend.js`` (re-stage the bundled copy),
  2. boot the staged backend on a free localhost port via uvicorn,
  3. probe ``/health`` and assert the reported version matches
     ``config/app_config.json``.

Skipped when Node.js is absent (the stager needs it) or when uvicorn is unable
to import the staged backend (e.g. missing optional deps in a minimal env).
No network or paid service is contacted; everything stays on 127.0.0.1.
"""

from __future__ import annotations

import json
import os
import shutil
import socket
import subprocess
import sys
import threading
import time
from pathlib import Path

import pytest

try:
    import urllib.request
except ImportError:  # pragma: no cover - stdlib always present on CPython
    urllib = None  # type: ignore

ROOT = Path(__file__).resolve().parents[1]
STAGED = ROOT / "desktop_shell" / "src-tauri" / "bundled_app"
STAGER = ROOT / "desktop_shell" / "stage-backend.js"
CONFIG = ROOT / "config" / "app_config.json"


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _wait_for_health(port: int, timeout: float = 30.0) -> dict:
    url = f"http://127.0.0.1:{port}/health"
    deadline = time.monotonic() + timeout
    last_err: Exception | None = None
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=2) as r:  # noqa: S310 - localhost
                if r.status == 200:
                    return json.loads(r.read().decode())
        except Exception as exc:  # pragma: no cover - startup race
            last_err = exc
            time.sleep(0.5)
    raise AssertionError(f"staged backend /health never responded: {last_err}")


@pytest.fixture(scope="module")
def staged_backend_proc():
    if urllib is None or shutil.which("node") is None:
        pytest.skip("node or urllib unavailable for bundled-backend smoke")
    # Re-stage to guarantee the bundled copy matches the current source.
    subprocess.run(["node", str(STAGER)], check=True, cwd=str(ROOT))
    if not (STAGED / "backend" / "main.py").is_file():
        pytest.skip("staged backend entrypoint missing after staging")

    port = _free_port()
    # Inherit the parent env (PATH especially) and just inject PYTHONPATH so the
    # staged `backend.*` namespace resolves from the bundled_app directory.
    env = dict(os.environ)
    env["PYTHONPATH"] = str(STAGED)
    env["PYTHONUNBUFFERED"] = "1"
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "backend.main:app",
         "--host", "127.0.0.1", "--port", str(port), "--no-access-log"],
        cwd=str(STAGED),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        env=env,
    )
    # Drain stdout on a background thread so the pipe buffer never fills and
    # blocks the subprocess (uvicorn logs continuously while serving).
    proc_log: list[str] = []

    def _reader() -> None:
        assert proc.stdout is not None
        for line in proc.stdout:
            proc_log.append(line.decode(errors="replace"))

    threading.Thread(target=_reader, daemon=True).start()
    try:
        yield port
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
        del proc_log  # discard log buffer kept in-process for simplicity


def test_staged_backend_health_responds(staged_backend_proc):
    port = staged_backend_proc
    body = _wait_for_health(port)
    assert body.get("status") == "ok"
    assert body.get("service") == "SessionGuard API"


def test_staged_backend_reports_canonical_version(staged_backend_proc):
    expected = json.loads(CONFIG.read_text()).get("version")
    port = staged_backend_proc
    body = _wait_for_health(port)
    assert body.get("version") == expected, (
        f"staged backend version {body.get('version')!r} != "
        f"config/app_config.json {expected!r} — stale-backend regression"
    )

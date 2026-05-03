"""
desktop_app/app/window.py
--------------------------
Phase 3 PySide6 desktop shell.

New in Phase 3:
  - Embedded browser via QWebEngineView (if available) — shows React frontend in-app
  - Falls back to external browser if QtWebEngine not installed
  - Start/stop/status for all three services
  - FFmpeg + Tesseract dependency check
  - Re-seed DB button
  - Persistent log with timestamps

Maturity: Working Prototype
Future:   Tauri native shell (V9 — already scaffolded in desktop_shell/).
"""

import subprocess
import sys
import shutil
import webbrowser
import urllib.request
import urllib.error
from datetime import datetime
from pathlib import Path

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QTextEdit, QGroupBox,
    QSplitter, QTabWidget, QFrame, QSizePolicy,
    QStatusBar,
)
from PySide6.QtCore  import Qt, QTimer, QUrl
from PySide6.QtGui   import QFont, QTextCursor

# Try to import WebEngine — optional
try:
    from PySide6.QtWebEngineWidgets import QWebEngineView
    HAS_WEBENGINE = True
except ImportError:
    HAS_WEBENGINE = False

ROOT = Path(__file__).resolve().parent.parent.parent

# ── Design tokens ─────────────────────────────────────────────────────────────
BG_BASE    = "#0a0c10"
BG_SURFACE = "#111318"
BG_ELEV    = "#1a1e26"
BG_BORDER  = "#242830"
TEXT_PRI   = "#e8eaf0"
TEXT_SEC   = "#8892a4"
TEXT_MUTED = "#4a5265"
ACCENT     = "#3b82f6"
GREEN      = "#22c55e"
RED        = "#ef4444"
AMBER      = "#f59e0b"

STYLESHEET = f"""
QMainWindow, QWidget {{
    background: {BG_BASE}; color: {TEXT_PRI};
    font-family: Inter, Segoe UI, sans-serif; font-size: 13px;
}}
QGroupBox {{
    border: 1px solid {BG_BORDER}; border-radius: 10px;
    margin-top: 10px; padding: 14px;
    font-weight: 600; color: {TEXT_SEC};
}}
QGroupBox::title {{ subcontrol-origin: margin; left: 12px; padding: 0 4px; }}
QPushButton {{
    background: {BG_SURFACE}; border: 1px solid {BG_BORDER};
    border-radius: 6px; padding: 8px 18px; color: {TEXT_PRI}; font-size: 13px;
}}
QPushButton:hover   {{ background: {BG_ELEV}; border-color: {ACCENT}; }}
QPushButton:pressed {{ background: #0d1117; }}
QPushButton:disabled {{ color: {TEXT_MUTED}; border-color: {BG_BORDER}; }}
QTextEdit {{
    background: {BG_SURFACE}; border: 1px solid {BG_BORDER};
    border-radius: 8px; color: {TEXT_SEC};
    font-family: JetBrains Mono, Consolas, monospace; font-size: 11px; padding: 8px;
}}
QTabWidget::pane   {{ border: 1px solid {BG_BORDER}; border-radius: 8px; }}
QTabBar::tab {{
    background: {BG_SURFACE}; color: {TEXT_SEC};
    padding: 8px 18px; border: 1px solid {BG_BORDER};
    border-bottom: none; border-radius: 6px 6px 0 0;
}}
QTabBar::tab:selected {{ background: {BG_ELEV}; color: {TEXT_PRI}; }}
QStatusBar {{ background: {BG_SURFACE}; color: {TEXT_MUTED}; font-size: 11px; }}
QSplitter::handle {{ background: {BG_BORDER}; }}
"""


class StatusDot(QLabel):
    def __init__(self): super().__init__("●"); self.setFont(QFont("Arial", 14)); self.set_unknown()
    def set_ok(self):      self.setStyleSheet(f"color: {GREEN};")
    def set_error(self):   self.setStyleSheet(f"color: {RED};")
    def set_unknown(self): self.setStyleSheet(f"color: {AMBER};")


class ServiceRow(QFrame):
    def __init__(self, name, action_label, on_action):
        super().__init__()
        lay = QHBoxLayout(self); lay.setContentsMargins(0, 4, 0, 4); lay.setSpacing(10)
        self.dot    = StatusDot()
        self.name   = QLabel(name); self.name.setMinimumWidth(180)
        self.status = QLabel("Checking…"); self.status.setStyleSheet(f"color: {TEXT_SEC}; font-size: 11px;")
        self.status.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.btn    = QPushButton(action_label); self.btn.setFixedWidth(130)
        self.btn.clicked.connect(on_action)
        for w in (self.dot, self.name, self.status, self.btn): lay.addWidget(w)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("SessionGuard v0.5 — Control Panel")
        self.setMinimumSize(1100, 700)
        self.setStyleSheet(STYLESHEET)

        self._backend_proc  = None
        self._frontend_proc = None

        self._build_ui()

        # Status poll every 4s
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._refresh_all_status)
        self._timer.start(4000)
        self._refresh_all_status()

    # ── UI construction ───────────────────────────────────────────────────────
    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Header bar
        header = QWidget(); header.setFixedHeight(56)
        header.setStyleSheet(f"background: {BG_SURFACE}; border-bottom: 1px solid {BG_BORDER};")
        hlay = QHBoxLayout(header); hlay.setContentsMargins(20, 0, 20, 0)
        title = QLabel("<span style='color:#3b82f6'>Session</span><span style='color:#e8eaf0'>Guard</span> v0.5")
        title.setTextFormat(Qt.RichText)
        title.setFont(QFont("Inter", 16, QFont.Bold))
        subtitle = QLabel("Intelligence · Review · Analysis")
        subtitle.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 11px;")
        hlay.addWidget(title); hlay.addSpacing(16); hlay.addWidget(subtitle); hlay.addStretch()
        root.addWidget(header)

        # Tabs
        tabs = QTabWidget()
        tabs.setDocumentMode(True)
        tabs.addTab(self._build_dashboard_tab(),  "Dashboard")
        tabs.addTab(self._build_services_tab(),   "Services")
        tabs.addTab(self._build_deps_tab(),        "Dependencies")
        root.addWidget(tabs)

        # Status bar
        self._status_bar = QStatusBar()
        self.setStatusBar(self._status_bar)
        self._status_bar.showMessage("SessionGuard v0.5 · Phase 3 Complete")

    # ── Tab: Dashboard (embedded browser or browser launcher) ─────────────────
    def _build_dashboard_tab(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w); lay.setContentsMargins(0, 0, 0, 0)

        if HAS_WEBENGINE:
            self._webview = QWebEngineView()
            self._webview.setUrl(QUrl("http://localhost:5173"))
            lay.addWidget(self._webview)
            self._log(f"[Desktop] Embedded browser → http://localhost:5173")
        else:
            placeholder = QWidget()
            phl = QVBoxLayout(placeholder); phl.setAlignment(Qt.AlignCenter)
            msg = QLabel(
                "<div style='text-align:center;color:#8892a4;'>"
                "<div style='font-size:40px;margin-bottom:16px;'>🌐</div>"
                "<div style='font-size:15px;font-weight:600;color:#e8eaf0;margin-bottom:8px;'>Dashboard</div>"
                "<div style='font-size:12px;margin-bottom:20px;'>Install PySide6-WebEngine to embed the dashboard here.</div>"
                "<code style='color:#3b82f6;background:#1a1e26;padding:4px 10px;border-radius:4px;font-size:12px;'>"
                "pip install PySide6-WebEngineWidgets</code>"
                "</div>"
            )
            msg.setTextFormat(Qt.RichText)
            msg.setAlignment(Qt.AlignCenter)
            phl.addWidget(msg)

            btn = QPushButton("Open Dashboard in Browser →")
            btn.setFixedWidth(260)
            btn.clicked.connect(lambda: webbrowser.open("http://localhost:5173"))
            phl.addSpacing(16)
            phl.addWidget(btn)
            lay.addWidget(placeholder)

        return w

    # ── Tab: Services ─────────────────────────────────────────────────────────
    def _build_services_tab(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w); lay.setContentsMargins(20, 20, 20, 20); lay.setSpacing(12)

        # Service rows
        svc = QGroupBox("Services")
        svc_lay = QVBoxLayout(svc); svc_lay.setSpacing(4)
        self._backend_row  = ServiceRow("Backend  (FastAPI :8000)", "Start",  self._toggle_backend)
        self._frontend_row = ServiceRow("Frontend (React   :5173)", "Start",  self._toggle_frontend)
        for row in (self._backend_row, self._frontend_row):
            svc_lay.addWidget(row)
        lay.addWidget(svc)

        # Quick actions
        act = QGroupBox("Quick Actions")
        act_lay = QHBoxLayout(act); act_lay.setSpacing(10)
        for label, fn in [
            ("🌐  Open Dashboard",  lambda: webbrowser.open("http://localhost:5173")),
            ("📡  Open API Docs",   lambda: webbrowser.open("http://127.0.0.1:8000/docs")),
            ("🗄   Re-seed DB",     self._reseed_db),
            ("📋  View Logs",       lambda: None),
        ]:
            b = QPushButton(label); b.clicked.connect(fn); act_lay.addWidget(b)
        lay.addWidget(act)

        # Log
        log_box = QGroupBox("Activity Log")
        log_lay = QVBoxLayout(log_box)
        self._log_widget = QTextEdit(); self._log_widget.setReadOnly(True); self._log_widget.setMinimumHeight(200)
        log_lay.addWidget(self._log_widget)
        lay.addWidget(log_box)

        lay.addStretch()
        return w

    # ── Tab: Dependencies ─────────────────────────────────────────────────────
    def _build_deps_tab(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w); lay.setContentsMargins(20, 20, 20, 20); lay.setSpacing(12)

        deps = QGroupBox("Dependency Status")
        deps_lay = QVBoxLayout(deps); deps_lay.setSpacing(4)
        self._ffmpeg_row   = ServiceRow("FFmpeg",         "Check", self._check_ffmpeg)
        self._tesseract_row = ServiceRow("Tesseract OCR",  "Check", self._check_tesseract)
        self._node_row     = ServiceRow("Node.js",         "Check", self._check_node)
        self._webeng_row   = ServiceRow("QtWebEngine",     "Check", self._check_webengine)
        for row in (self._ffmpeg_row, self._tesseract_row, self._node_row, self._webeng_row):
            deps_lay.addWidget(row)
        lay.addWidget(deps)

        # Phase status
        phase = QGroupBox("Phase 3 Engine Status")
        phase_lay = QVBoxLayout(phase)
        engine_list = [
            "✅ Analysis Engine       — real metrics, RTP, drawdown",
            "✅ Behavior Engine       — tilt, escalation, drift detection (sklearn)",
            "✅ OCR Engine            — Tesseract 5 field extraction + confidence",
            "✅ Live Engine           — mock + screen mode with autosave/checkpoints",
            "✅ Video Pipeline        — cv2 frame extraction + OCR pass + event building",
            "✅ CSV Parser            — spin-level & session-level auto-detection",
            "✅ PDF Export            — ReportLab 4.x with charts + event log",
            "✅ Excel Export          — openpyxl multi-sheet styled workbook",
            "✅ Comparison Engine     — multi-session diff with narrative",
            "✅ Review Queue Engine   — uncertain-first, accept/reject/correct",
        ]
        for e in engine_list:
            lbl = QLabel(e); lbl.setStyleSheet(f"color: {TEXT_SEC}; font-size: 12px; padding: 3px 0;")
            phase_lay.addWidget(lbl)
        lay.addWidget(phase)
        lay.addStretch()
        return w

    # ── Log ───────────────────────────────────────────────────────────────────
    def _log(self, msg: str):
        ts    = datetime.now().strftime("%H:%M:%S")
        text  = f"[{ts}] {msg}"
        try:
            self._log_widget.append(text)
            self._log_widget.moveCursor(QTextCursor.End)
        except Exception:
            pass
        self._status_bar.showMessage(text, 5000)

    # ── Status refresh ────────────────────────────────────────────────────────
    def _refresh_all_status(self):
        self._check_backend_status()
        self._check_frontend_status()
        self._check_ffmpeg()
        self._check_tesseract()
        self._check_node()
        self._check_webengine()

    def _ping(self, url: str) -> bool:
        try:
            urllib.request.urlopen(url, timeout=2)
            return True
        except Exception:
            return False

    def _check_backend_status(self):
        ok = self._ping("http://127.0.0.1:8000/health")
        self._backend_row.dot.set_ok() if ok else self._backend_row.dot.set_error()
        self._backend_row.status.setText("Running · http://127.0.0.1:8000" if ok else "Not running")
        self._backend_row.btn.setText("Stop" if ok else "Start")

    def _check_frontend_status(self):
        ok = self._ping("http://localhost:5173")
        self._frontend_row.dot.set_ok() if ok else self._frontend_row.dot.set_error()
        self._frontend_row.status.setText("Running · http://localhost:5173" if ok else "Not running")
        self._frontend_row.btn.setText("Stop" if ok else "Start")

    def _check_ffmpeg(self):
        path = shutil.which("ffmpeg")
        ok   = bool(path)
        self._ffmpeg_row.dot.set_ok() if ok else self._ffmpeg_row.dot.set_error()
        self._ffmpeg_row.status.setText(f"Found: {path}" if ok else "Not found — install from ffmpeg.org")

    def _check_tesseract(self):
        path = shutil.which("tesseract")
        ok   = bool(path)
        self._tesseract_row.dot.set_ok() if ok else self._tesseract_row.dot.set_error()
        self._tesseract_row.status.setText(f"Found: {path}" if ok else "Not found — install Tesseract 5")

    def _check_node(self):
        path = shutil.which("node")
        ok   = bool(path)
        self._node_row.dot.set_ok() if ok else self._node_row.dot.set_error()
        self._node_row.status.setText(f"Found: {path}" if ok else "Not found — install from nodejs.org")

    def _check_webengine(self):
        self._webeng_row.dot.set_ok() if HAS_WEBENGINE else self._webeng_row.dot.set_unknown()
        self._webeng_row.status.setText(
            "Available — dashboard embedded in app" if HAS_WEBENGINE
            else "Not installed — pip install PySide6-WebEngineWidgets"
        )

    # ── Service controls ──────────────────────────────────────────────────────
    def _toggle_backend(self):
        if self._backend_proc and self._backend_proc.poll() is None:
            self._backend_proc.terminate(); self._backend_proc = None
            self._log("[Backend] Stopped.")
        else:
            cmd = [sys.executable, "-m", "uvicorn", "backend.main:app",
                   "--host", "127.0.0.1", "--port", "8000", "--reload"]
            self._backend_proc = subprocess.Popen(cmd, cwd=str(ROOT),
                                                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            self._log("[Backend] Starting on http://127.0.0.1:8000 …")
        self._check_backend_status()

    def _toggle_frontend(self):
        if self._frontend_proc and self._frontend_proc.poll() is None:
            self._frontend_proc.terminate(); self._frontend_proc = None
            self._log("[Frontend] Stopped.")
        else:
            npm = shutil.which("npm")
            if not npm:
                self._log("[Frontend] ERROR — npm not found on PATH."); return
            self._frontend_proc = subprocess.Popen(
                [npm, "run", "dev"], cwd=str(ROOT / "frontend"),
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            )
            self._log("[Frontend] Starting on http://localhost:5173 …")
        self._check_frontend_status()

    def _reseed_db(self):
        try:
            sys.path.insert(0, str(ROOT))
            from database.db import init_db, init_db_v2, seed_demo_data
            init_db(); init_db_v2(); seed_demo_data(force=True)
            self._log("[DB] Re-seeded with 12 demo sessions.")
            if HAS_WEBENGINE:
                self._webview.reload()
        except Exception as e:
            self._log(f"[DB] Reseed failed: {e}")

    def closeEvent(self, event):
        for proc in (self._backend_proc, self._frontend_proc):
            if proc and proc.poll() is None: proc.terminate()
        event.accept()

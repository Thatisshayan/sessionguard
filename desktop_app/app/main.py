"""
desktop_app/app/main.py
------------------------
Entry point for the PySide6 desktop shell.
Launches the main window and checks dependencies on startup.

Maturity: Working Prototype
Future:   Embed backend/frontend process management here (V7).
          Add system tray icon, one-command orchestration (V9).
"""

import sys
from pathlib import Path

# ── Ensure project root is on sys.path ───────────────────────────────────────
ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def main():
    try:
        from PySide6.QtWidgets import QApplication
    except ImportError:
        print("[ERROR] PySide6 not installed.")
        print("        Run: pip install PySide6")
        sys.exit(1)

    from desktop_app.app.window import MainWindow

    app = QApplication(sys.argv)
    app.setApplicationName("SessionGuard")
    app.setApplicationVersion("0.4.0")

    # Dark palette handled via stylesheet in MainWindow
    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()

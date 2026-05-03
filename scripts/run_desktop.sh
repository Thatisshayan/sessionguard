#!/usr/bin/env bash
# run_desktop.sh — Start the PySide6 desktop shell (Mac/Linux)

set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/.."

echo "[SessionGuard] Starting desktop shell..."

if ! command -v python3 &>/dev/null; then
    echo "[ERROR] python3 not found on PATH."
    exit 1
fi

python3 -m desktop_app.app.main

#!/usr/bin/env bash
# run_backend.sh — Start the FastAPI backend server (Mac/Linux)

set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/.."

echo "[SessionGuard] Starting backend..."

if ! command -v python3 &>/dev/null; then
    echo "[ERROR] python3 not found on PATH."
    echo "        Install Python from https://python.org and re-run."
    exit 1
fi

python3 -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload

#!/usr/bin/env bash
# run_frontend.sh — Start the React frontend dev server (Mac/Linux)

set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/../frontend"

echo "[SessionGuard] Starting frontend..."

if ! command -v node &>/dev/null; then
    echo "[ERROR] Node.js not found on PATH."
    echo "        Install from https://nodejs.org and re-run."
    exit 1
fi

if [ ! -d "node_modules" ]; then
    echo "[SessionGuard] Installing frontend dependencies..."
    npm install
fi

npm run dev

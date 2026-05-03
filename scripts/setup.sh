#!/usr/bin/env bash
# setup.sh — First-time setup for Mac/Linux. Phase 3 complete.
set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$SCRIPT_DIR/.."
cd "$ROOT"

echo "============================================"
echo " SessionGuard v0.5 — First Time Setup"
echo "============================================"
echo ""

echo "[1/5] Checking Python..."
if ! command -v python3 &>/dev/null; then
    echo "[ERROR] python3 not found. Install via: brew install python  OR  sudo apt install python3"; exit 1
fi
python3 --version && echo "[OK]"

echo "[2/5] Installing Python dependencies..."
python3 -m pip install --upgrade pip --quiet
python3 -m pip install -r requirements.txt
echo "[OK] Python deps installed"

echo "[3/5] Checking Node.js..."
if ! command -v node &>/dev/null; then
    echo "[ERROR] Node.js not found. Install from: https://nodejs.org"; exit 1
fi
node --version && echo "[OK]"

echo "[4/5] Installing frontend dependencies..."
cd "$ROOT/frontend"
[ ! -d "node_modules" ] && npm install
cd "$ROOT"
echo "[OK] Frontend deps installed"

echo "[5/5] Checking optional dependencies..."
for bin in ffmpeg tesseract; do
    if command -v $bin &>/dev/null; then
        echo "[OK] $bin found: $(which $bin)"
    else
        echo "[WARN] $bin not found — install for video/OCR features"
        case $bin in
            ffmpeg)    echo "      brew install ffmpeg  OR  sudo apt install ffmpeg";;
            tesseract) echo "      brew install tesseract  OR  sudo apt install tesseract-ocr";;
        esac
    fi
done

chmod +x scripts/*.sh
echo ""
echo "============================================"
echo " Setup complete."
echo " Run: bash scripts/run_all.sh"
echo "============================================"

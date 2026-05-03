#!/usr/bin/env bash
# build_installer.sh — SessionGuard native installer (Mac/Linux)
set -e
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

echo ""
echo "============================================================"
echo " SessionGuard v1.0 — Native Installer Build"
echo "============================================================"
echo ""

# ── Check dependencies ────────────────────────────────────────────────────────
echo "[1/6] Checking dependencies..."

if ! command -v rustc &>/dev/null; then
    echo ""
    echo " [ERROR] Rust is not installed."
    echo " Install it: curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh"
    echo " Then restart your terminal and run this script again."
    echo ""
    exit 1
fi
echo " Rust: $(rustc --version)"

if ! command -v node &>/dev/null; then
    echo " [ERROR] Node.js not found. Install from https://nodejs.org"
    exit 1
fi
echo " Node: $(node --version)"

if ! command -v python3 &>/dev/null; then
    echo " [ERROR] Python3 not found."
    exit 1
fi
echo " Python: $(python3 --version)"

# Mac-specific: check Xcode CLT
if [[ "$OSTYPE" == "darwin"* ]]; then
    if ! xcode-select -p &>/dev/null; then
        echo " [ERROR] Xcode Command Line Tools required on Mac."
        echo " Install: xcode-select --install"
        exit 1
    fi
    echo " Xcode CLT: OK"
fi

echo " All dependencies found."
echo ""

# ── Build React frontend ──────────────────────────────────────────────────────
echo "[2/6] Building React frontend..."
cd "$ROOT/frontend"
[ ! -d "node_modules" ] && npm install
npm run build
echo " Frontend built."
echo ""

# ── Install Tauri CLI ─────────────────────────────────────────────────────────
echo "[3/6] Installing Tauri CLI..."
cd "$ROOT/desktop_shell"
[ ! -d "node_modules" ] && npm install
echo " Tauri CLI ready."
echo ""

# ── Build ─────────────────────────────────────────────────────────────────────
echo "[4/6] Building Tauri application (5-15 min first time)..."
npm run tauri:build
echo ""

# ── Find output ───────────────────────────────────────────────────────────────
echo "[5/6] Locating installer..."
BUNDLE_DIR="$ROOT/desktop_shell/src-tauri/target/release/bundle"
if [[ "$OSTYPE" == "darwin"* ]]; then
    INSTALLER=$(find "$BUNDLE_DIR/dmg" -name "*.dmg" 2>/dev/null | head -1)
    INSTALLER2=$(find "$BUNDLE_DIR/macos" -name "*.app" 2>/dev/null | head -1)
else
    INSTALLER=$(find "$BUNDLE_DIR/appimage" -name "*.AppImage" 2>/dev/null | head -1)
    INSTALLER2=$(find "$BUNDLE_DIR/deb" -name "*.deb" 2>/dev/null | head -1)
fi

echo ""
echo "[6/6] Done!"
echo ""
echo "============================================================"
echo " Output files:"
if [ -n "$INSTALLER" ]; then
    echo "   $INSTALLER"
fi
if [ -n "$INSTALLER2" ]; then
    echo "   $INSTALLER2"
fi
echo ""
echo " On Mac: drag SessionGuard.app to /Applications"
echo " On Linux: chmod +x SessionGuard.AppImage && ./SessionGuard.AppImage"
echo "============================================================"
echo ""

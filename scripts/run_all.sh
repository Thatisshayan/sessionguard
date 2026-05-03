#!/usr/bin/env bash
# run_all.sh — Launch backend, frontend, and desktop shell together (Mac/Linux)
# Each service runs in its own terminal tab/process.

set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "[SessionGuard] Launching all services..."
echo ""
echo "  Backend  -> http://127.0.0.1:8000"
echo "  Frontend -> http://localhost:5173"
echo "  Desktop  -> PySide6 window"
echo ""

# Make scripts executable
chmod +x "$SCRIPT_DIR/run_backend.sh"
chmod +x "$SCRIPT_DIR/run_frontend.sh"
chmod +x "$SCRIPT_DIR/run_desktop.sh"

# Launch each in background, log to file
"$SCRIPT_DIR/run_backend.sh"  > /tmp/sg_backend.log  2>&1 &
BACKEND_PID=$!
echo "[SessionGuard] Backend PID: $BACKEND_PID"

sleep 3

"$SCRIPT_DIR/run_frontend.sh" > /tmp/sg_frontend.log 2>&1 &
FRONTEND_PID=$!
echo "[SessionGuard] Frontend PID: $FRONTEND_PID"

sleep 2

"$SCRIPT_DIR/run_desktop.sh"  > /tmp/sg_desktop.log  2>&1 &
DESKTOP_PID=$!
echo "[SessionGuard] Desktop PID: $DESKTOP_PID"

echo ""
echo "[SessionGuard] All services running."
echo "  Logs: /tmp/sg_backend.log | /tmp/sg_frontend.log | /tmp/sg_desktop.log"
echo "  Press Ctrl+C to stop all."
echo ""

# Wait and clean up on exit
trap "kill $BACKEND_PID $FRONTEND_PID $DESKTOP_PID 2>/dev/null; echo '[SessionGuard] All services stopped.'" EXIT
wait

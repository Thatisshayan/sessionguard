@echo off
:: run_frontend.bat — Start the React frontend dev server.

setlocal
set "ROOT=%~dp0"
cd /d "%ROOT%..\frontend"

echo [SessionGuard] Starting frontend...

where node >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Node.js not found on PATH.
    echo         Install from https://nodejs.org and re-run.
    pause
    exit /b 1
)

where npm >nul 2>&1
if errorlevel 1 (
    echo [ERROR] npm not found on PATH.
    pause
    exit /b 1
)

if not exist "node_modules" (
    echo [SessionGuard] Installing frontend dependencies...
    npm install
)

npm run dev
pause

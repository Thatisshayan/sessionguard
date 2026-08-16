@echo off
:: run_desktop.bat — Start the Tauri desktop shell in local dev mode.

setlocal
set "ROOT=%~dp0"
cd /d "%ROOT%..\desktop_shell"

echo [SessionGuard] Starting desktop shell...

where node >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Node.js not found on PATH.
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
    echo [SessionGuard] Installing desktop shell dependencies...
    npm install
)

npm run tauri:dev
pause

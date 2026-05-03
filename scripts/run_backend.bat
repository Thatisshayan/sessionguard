@echo off
:: run_backend.bat
:: Starts the FastAPI backend server.
:: Uses %~dp0 so this works regardless of where the folder lives or what spaces are in the path.

setlocal
set "ROOT=%~dp0"
cd /d "%ROOT%"

echo [SessionGuard] Starting backend...

where python >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found on PATH.
    echo         Install Python from https://python.org and re-run.
    pause
    exit /b 1
)

python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
pause

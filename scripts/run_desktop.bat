@echo off
:: run_desktop.bat — Start the PySide6 desktop shell.

setlocal
set "ROOT=%~dp0"
cd /d "%ROOT%.."

echo [SessionGuard] Starting desktop shell...

where python >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found on PATH.
    pause
    exit /b 1
)

python -m desktop_app.app.main
pause

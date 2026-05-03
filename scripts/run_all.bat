@echo off
:: run_all.bat — Launch backend, frontend, and desktop shell together.
:: Opens each in its own window so logs are visible separately.

setlocal
set "ROOT=%~dp0"

echo [SessionGuard] Launching all services...
echo.
echo   Backend  -> http://127.0.0.1:8000
echo   Frontend -> http://localhost:5173
echo   Desktop  -> PySide6 window
echo.

start "SessionGuard Backend"  cmd /k ""%ROOT%run_backend.bat""
timeout /t 3 /nobreak >nul
start "SessionGuard Frontend" cmd /k ""%ROOT%run_frontend.bat""
timeout /t 2 /nobreak >nul
start "SessionGuard Desktop"  cmd /k ""%ROOT%run_desktop.bat""

echo [SessionGuard] All services launching. Check individual windows for errors.

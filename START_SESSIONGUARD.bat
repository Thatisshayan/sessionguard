@echo off
REM SessionGuard Startup Script v1.2.0
REM IMPORTANT: Set ANTHROPIC_API_KEY environment variable before running
REM   setx ANTHROPIC_API_KEY "your_api_key_here"
REM   Then restart this terminal

echo Killing old processes...
powershell -NoProfile -ExecutionPolicy Bypass -Command "Get-NetTCPConnection -LocalPort 8000,5173 -State Listen -ErrorAction SilentlyContinue | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }"
taskkill /F /IM node.exe /T >nul 2>&1
ping -n 3 127.0.0.1 >nul

echo Starting backend...
set PYTHONPATH=C:\Projects\SessionGuard\sessionguard
start "SG-Backend" /MIN cmd /k "set PYTHONPATH=C:\Projects\SessionGuard\sessionguard && cd /d C:\Projects\SessionGuard\sessionguard && C:\Users\Shaya\AppData\Local\Programs\Python\Python312\Scripts\uvicorn.exe backend.main:app --host 127.0.0.1 --port 8000 --no-access-log"
ping -n 6 127.0.0.1 >nul

echo Starting frontend...
start "SG-Frontend" /MIN cmd /k "cd /d C:\Projects\SessionGuard\sessionguard\frontend && C:\Program Files\nodejs\npm.cmd run dev"
ping -n 5 127.0.0.1 >nul

echo Done. Opening browser...
start "" "http://localhost:5173"

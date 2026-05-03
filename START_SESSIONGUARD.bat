@echo off
title SessionGuard v1.2.0
cd /d C:\Projects\SessionGuard\sessionguard

echo [1/3] Stopping old processes...
powershell -NoProfile -ExecutionPolicy Bypass -Command "Get-NetTCPConnection -LocalPort 8000,5173 -State Listen -ErrorAction SilentlyContinue | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }"
taskkill /F /IM node.exe /T >nul 2>&1
timeout /t 2 /nobreak >nul

echo [2/3] Starting backend...
set PYTHONPATH=C:\Projects\SessionGuard\sessionguard
start "SG Backend" /MIN C:\Users\Shaya\AppData\Local\Programs\Python\Python312\Scripts\uvicorn.exe backend.main:app --host 127.0.0.1 --port 8000 --no-access-log
timeout /t 4 /nobreak >nul

echo [3/3] Starting frontend...
start "SG Frontend" /MIN cmd /c "cd /d C:\Projects\SessionGuard\sessionguard\frontend && C:\Program Files\nodejs\npm.cmd run dev"
timeout /t 3 /nobreak >nul

echo.
echo ==========================================
echo  SessionGuard v1.2.0 is running
echo  Dashboard : http://localhost:5173
echo  API Docs  : http://127.0.0.1:8000/docs
echo  Login     : demo@sessionguard.local
echo  Password  : demo123
echo ==========================================
echo.
start "" http://localhost:5173
pause

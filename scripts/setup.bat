@echo off
:: setup.bat — First-time setup. Phase 3 complete.
setlocal
set "ROOT=%~dp0.."
cd /d "%ROOT%"
echo ============================================
echo  SessionGuard v0.5 - First Time Setup
echo ============================================
echo.
echo [1/5] Checking Python...
where python >nul 2>&1 || (echo [ERROR] Python not found. Download: https://python.org & pause & exit /b 1)
python --version & echo [OK]
echo [2/5] Installing Python deps...
python -m pip install --upgrade pip --quiet
python -m pip install -r requirements.txt
echo [OK]
echo [3/5] Checking Node.js...
where node >nul 2>&1 || (echo [ERROR] Node.js not found. Download: https://nodejs.org & pause & exit /b 1)
node --version & echo [OK]
echo [4/5] Installing frontend deps...
cd /d "%ROOT%\frontend"
if not exist "node_modules" npm install
cd /d "%ROOT%"
echo [OK]
echo [5/5] Checking optional deps...
where ffmpeg >nul 2>&1 && echo [OK] FFmpeg found || echo [WARN] FFmpeg not found - https://ffmpeg.org
where tesseract >nul 2>&1 && echo [OK] Tesseract found || echo [WARN] Tesseract not found - https://github.com/tesseract-ocr/tesseract
echo.
echo ============================================
echo  Setup complete. Run scripts\run_all.bat
echo ============================================
pause

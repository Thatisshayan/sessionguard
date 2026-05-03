@echo off
setlocal enabledelayedexpansion
set "ROOT=%~dp0"
cd /d "%ROOT%"

echo.
echo ============================================================
echo  SessionGuard v1.0 - Windows Installer Build
echo ============================================================
echo.

REM ── Step 1: Check dependencies ──────────────────────────────────────────────
echo [1/7] Checking dependencies...

where rustc >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo  [ERROR] Rust is not installed.
    echo.
    echo  Install it now - takes about 5 minutes:
    echo    1. Go to: https://rustup.rs
    echo    2. Download and run rustup-init.exe
    echo    3. Press 1 for default installation
    echo    4. Close and reopen this window when done
    echo    5. Run this script again
    echo.
    pause & exit /b 1
)
for /f "tokens=*" %%v in ('rustc --version') do set RUST_VER=%%v
echo  Rust: !RUST_VER!

where node >nul 2>&1
if %errorlevel% neq 0 (
    echo  [ERROR] Node.js not found. Install from https://nodejs.org
    pause & exit /b 1
)
for /f "tokens=*" %%v in ('node --version') do set NODE_VER=%%v
echo  Node: !NODE_VER!

where python >nul 2>&1
if %errorlevel% neq 0 (
    echo  [ERROR] Python not found. Install from https://python.org
    pause & exit /b 1
)
for /f "tokens=*" %%v in ('python --version') do set PY_VER=%%v
echo  Python: !PY_VER!

echo  All dependencies found.
echo.

REM ── Step 2: Build React frontend ────────────────────────────────────────────
echo [2/7] Building React frontend...
cd /d "%ROOT%frontend"
if not exist "node_modules" (
    echo  Installing frontend dependencies...
    call npm install
    if %errorlevel% neq 0 ( echo  [ERROR] npm install failed. & pause & exit /b 1 )
)
call npm run build
if %errorlevel% neq 0 (
    echo  [ERROR] Frontend build failed. Check the error above.
    pause & exit /b 1
)
echo  Frontend built successfully.
echo.

REM ── Step 3: Install Tauri CLI ────────────────────────────────────────────────
echo [3/7] Installing Tauri CLI...
cd /d "%ROOT%desktop_shell"
if not exist "node_modules" (
    call npm install
    if %errorlevel% neq 0 ( echo  [ERROR] npm install failed. & pause & exit /b 1 )
)
echo  Tauri CLI ready.
echo.

REM ── Step 4: Install WebView2 runtime (required on Windows) ──────────────────
echo [4/7] Checking WebView2 runtime...
reg query "HKLM\SOFTWARE\WOW6432Node\Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}" >nul 2>&1
if %errorlevel% neq 0 (
    echo  WebView2 not found. Downloading bootstrapper...
    powershell -Command "Invoke-WebRequest -Uri 'https://go.microsoft.com/fwlink/p/?LinkId=2124703' -OutFile 'MicrosoftEdgeWebview2Setup.exe'"
    echo  Installing WebView2 (may require admin)...
    MicrosoftEdgeWebview2Setup.exe /silent /install
    del MicrosoftEdgeWebview2Setup.exe 2>nul
    echo  WebView2 installed.
) else (
    echo  WebView2 already installed.
)
echo.

REM ── Step 5: Build the Tauri app ──────────────────────────────────────────────
echo [5/7] Building Tauri application (this takes 5-15 minutes first time)...
echo  Rust is compiling... grab a coffee.
echo.
cd /d "%ROOT%desktop_shell"
call npm run tauri:build
if %errorlevel% neq 0 (
    echo.
    echo  [ERROR] Tauri build failed.
    echo  Common causes:
    echo    - Rust linker not found: install Visual Studio Build Tools
    echo      https://visualstudio.microsoft.com/visual-cpp-build-tools/
    echo    - Frontend dist/ not found: check step 2 above
    echo    - Permission error: run as Administrator
    echo.
    pause & exit /b 1
)
echo.

REM ── Step 6: Find the installer ───────────────────────────────────────────────
echo [6/7] Locating installer...
set "INSTALLER="
for /r "%ROOT%desktop_shell\src-tauri\target\release\bundle" %%f in (*.msi *.exe) do (
    if "!INSTALLER!"=="" set "INSTALLER=%%f"
)

if "!INSTALLER!"=="" (
    echo  [WARN] Could not locate installer automatically.
    echo  Check: desktop_shell\src-tauri\target\release\bundle\
) else (
    echo  Installer found: !INSTALLER!
)
echo.

REM ── Step 7: Done ─────────────────────────────────────────────────────────────
echo [7/7] Build complete!
echo.
echo ============================================================
echo  SessionGuard v1.0 Windows Installer
echo ============================================================
echo.
if "!INSTALLER!" neq "" (
    echo  Installer: !INSTALLER!
    echo.
    echo  Double-click that file to install SessionGuard on any Windows machine.
    echo  It includes the dashboard, all engines, and starts on login.
    echo.
    echo  Open installer now? [Y/N]
    set /p OPEN_NOW=
    if /i "!OPEN_NOW!"=="Y" start "" "!INSTALLER!"
) else (
    echo  Find your installer in:
    echo  desktop_shell\src-tauri\target\release\bundle\msi\
    echo  desktop_shell\src-tauri\target\release\bundle\nsis\
)
echo.
pause

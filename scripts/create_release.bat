@echo off
setlocal EnableExtensions EnableDelayedExpansion
cd /d "%~dp0"
echo.
echo ======================================
echo  SessionGuard Release Builder
echo ======================================
echo.
where gh >nul 2>nul
if errorlevel 1 ( echo ERROR: Install gh CLI from https://cli.github.com then run: gh auth login & exit /b 1 )
where npm >nul 2>nul
if errorlevel 1 ( echo ERROR: npm not found. & exit /b 1 )
if not exist "config\app_config.json" ( echo ERROR: config\app_config.json missing. & exit /b 1 )

echo Bumping patch version...
powershell -NoProfile -ExecutionPolicy Bypass -Command "$p='config/app_config.json';$j=Get-Content $p -Raw|ConvertFrom-Json;$parts=($j.version -replace '^v','').Split('.');while($parts.Count -lt 3){$parts+='0'};$j.version=('{0}.{1}.{2}' -f [int]$parts[0],[int]$parts[1],([int]$parts[2]+1));$j|ConvertTo-Json -Depth 50|Set-Content $p -Encoding UTF8;Write-Output $j.version" > .ver.tmp
set /p VERSION=<.ver.tmp & del .ver.tmp
if "%VERSION%"=="" ( echo ERROR: Version bump failed. & exit /b 1 )
echo New version: %VERSION%

echo Building frontend...
pushd frontend & call npm install & call npm run build & popd
if errorlevel 1 ( echo ERROR: Frontend build failed. & exit /b 1 )

echo Building Tauri installer...
pushd desktop_shell & call npm install & call npm run tauri:build & popd
if errorlevel 1 ( echo ERROR: Tauri build failed. & exit /b 1 )

set ASSETS=
for %%F in ("desktop_shell\src-tauri\target\release\bundle\nsis\*.exe") do set ASSETS=!ASSETS! "%%~fF"
for %%F in ("desktop_shell\src-tauri\target\release\bundle\msi\*.msi") do set ASSETS=!ASSETS! "%%~fF"
if "!ASSETS!"=="" ( echo ERROR: No installer files found. & exit /b 1 )

echo Creating GitHub release v%VERSION%...
gh release create "v%VERSION%" !ASSETS! --title "SessionGuard v%VERSION%" --notes "Release v%VERSION%"
if errorlevel 1 ( echo ERROR: GitHub release failed. & exit /b 1 )

echo.
echo ====================================
echo  Done: v%VERSION% released!
echo ====================================
endlocal

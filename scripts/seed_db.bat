@echo off
:: seed_db.bat — Re-seed the database with fresh demo data.
:: WARNING: This deletes all existing data. Use for dev/testing only.

setlocal
set "ROOT=%~dp0.."
cd /d "%ROOT%"

echo [SessionGuard] Re-seeding database with demo data...
echo WARNING: This will DELETE all existing data.
echo.
set /p CONFIRM="Type YES to continue: "
if /i not "%CONFIRM%"=="YES" (
    echo Cancelled.
    pause
    exit /b 0
)

python -c "from database.db import init_db, seed_demo_data; init_db(); seed_demo_data(force=True)"
echo [SessionGuard] Database seeded successfully.
pause

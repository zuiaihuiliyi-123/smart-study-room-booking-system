@echo off
rem ============================================================
rem  Smart Study Room - reset demo bookings/violations/...
rem
rem  Deletes demo-account business data and closures whose
rem  reason starts with the demo prefix, then recreates the
rem  dataset relative to the current time.
rem
rem  Requires backend\.venv created by start.bat.
rem ============================================================
setlocal EnableExtensions
chcp 65001 >nul
cd /d "%~dp0"

echo.
echo ============================================================
echo    Smart Study Room - Reset demo data
echo ============================================================
echo.

if not exist "backend\.venv\Scripts\python.exe" goto :no_venv

set "PYTHONUTF8=1"
pushd "backend"
".venv\Scripts\python.exe" -m scripts.seed_demo_data --reset
set "RC=%ERRORLEVEL%"
popd

echo.
if "%RC%"=="0" (
    echo [ok] Demo data has been reset.
) else (
    echo [ERROR] Reset failed with exit code %RC%.
    echo         Make sure MySQL is running and backend\.env is valid.
)
echo.
echo Press any key to close this window.
pause >nul
exit /b %RC%

:no_venv
echo [ERROR] backend\.venv was not found.
echo         Run start.bat first to create the environment.
echo.
echo Press any key to close this window.
pause >nul
exit /b 1

@echo off
rem ============================================================
rem  Smart Study Room - stop the launcher windows
rem
rem  Closes the "SSR Backend" / "SSR Frontend" windows started by
rem  start.bat, then kills anything still listening on 8000/5173.
rem  The MySQL service is intentionally left running: it is shared
rem  with other applications and may need administrator rights.
rem ============================================================
setlocal EnableExtensions
chcp 65001 >nul
cd /d "%~dp0"
title Smart Study Room - Stop

echo.
echo ============================================================
echo    Smart Study Room - Stop
echo ============================================================
echo.

set "FOUND=0"
call :port_in_use 8000
if not errorlevel 1 set "FOUND=1"
call :port_in_use 5173
if not errorlevel 1 set "FOUND=1"
if "%FOUND%"=="0" goto :nothing

echo The following ports are in use:
netstat -ano | findstr /r /c:":8000 " /c:":5173 " | findstr /i "LISTENING"
echo.
set "CONFIRM="
set /p "CONFIRM=Stop the backend and frontend now? [Y/N]: "
if /i not "%CONFIRM%"=="Y" goto :cancel

echo.
echo Closing launcher windows...
taskkill /FI "WINDOWTITLE eq SSR Backend*" /T /F >nul 2>&1
taskkill /FI "WINDOWTITLE eq SSR Frontend*" /T /F >nul 2>&1
call :kill_port 8000
call :kill_port 5173
echo.
echo [ok] Backend and frontend stopped. MySQL was left running.
goto :end

:nothing
echo Nothing is listening on ports 8000 or 5173.
goto :end

:cancel
echo Cancelled.

:end
echo.
echo Press any key to close this window.
pause >nul
exit /b 0

:kill_port
for /f "tokens=5" %%p in ('netstat -ano ^| findstr /r /c:":%~1 " ^| findstr /i "LISTENING"') do (
    taskkill /PID %%p /T /F >nul 2>&1
    if not errorlevel 1 echo   [ok] Stopped process %%p on port %~1
)
exit /b 0

:port_in_use
netstat -ano | findstr /r /c:":%~1 " | findstr /i "LISTENING" >nul
if errorlevel 1 exit /b 1
exit /b 0

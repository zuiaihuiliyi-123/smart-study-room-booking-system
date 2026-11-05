@echo off
rem ============================================================
rem  Smart Study Room - one-click launcher (Windows)
rem
rem  ASCII-only messages: cmd may parse a .bat file with the OEM
rem  code page, so Chinese text can break parsing on some machines.
rem
rem  Steps:
rem    1. check Python and Node.js
rem    2. create backend\.venv and install backend dependencies
rem    3. start the local MySQL service when it is not running
rem    4. create backend\.env, the database and the app account
rem    5. apply Alembic migrations and seed demo data
rem    6. install frontend dependencies, start both servers
rem
rem  Every step is idempotent: running this file again is safe.
rem  Usage: start.bat [--no-browser]
rem ============================================================
setlocal EnableExtensions
chcp 65001 >nul
cd /d "%~dp0"

set "ROOT=%CD%"
set "BACKEND=%ROOT%\backend"
set "FRONTEND=%ROOT%\frontend"
set "VENV_PY=%BACKEND%\.venv\Scripts\python.exe"
set "NO_BROWSER=0"
if /i "%~1"=="--no-browser" set "NO_BROWSER=1"

title Smart Study Room - One-click Launcher
echo.
echo ============================================================
echo    Smart Study Room - One-click Launcher
echo ============================================================
echo.

if not exist "%BACKEND%\requirements.txt" goto :not_project
if not exist "%FRONTEND%\package.json" goto :not_project

rem ---------- 1. Python 3.11+ ----------
set "PYTHON_CMD="
py -3 -c "import sys; sys.exit(0 if sys.version_info >= (3,11) else 1)" >nul 2>nul
if not errorlevel 1 set "PYTHON_CMD=py -3"
if not defined PYTHON_CMD (
    python -c "import sys; sys.exit(0 if sys.version_info >= (3,11) else 1)" >nul 2>nul
    if not errorlevel 1 set "PYTHON_CMD=python"
)
if not defined PYTHON_CMD goto :no_python
echo [ok] Python 3.11+ found (%PYTHON_CMD%).

rem ---------- 2. Node.js 18+ ----------
where node >nul 2>nul
if errorlevel 1 goto :no_node
where npm >nul 2>nul
if errorlevel 1 goto :no_node
set "NODE_MAJOR="
for /f "delims=." %%v in ('node -p "process.versions.node" 2^>nul') do set "NODE_MAJOR=%%v"
if not defined NODE_MAJOR goto :no_node
if %NODE_MAJOR% LSS 18 goto :old_node
echo [ok] Node.js %NODE_MAJOR%.x found.

rem ---------- 3. Backend virtual environment ----------
if exist "%VENV_PY%" goto :venv_ready
echo [1/6] Creating Python virtual environment (backend\.venv)...
%PYTHON_CMD% -m venv "%BACKEND%\.venv"
if errorlevel 1 goto :venv_failed
echo       Done.

:venv_ready
call :install_backend_deps
if errorlevel 1 goto :pip_failed

rem ---------- 4. MySQL service ----------
echo [3/6] Checking MySQL...
cd /d "%BACKEND%"
"%VENV_PY%" -m scripts.bootstrap_db probe
set "PROBE_RC=%ERRORLEVEL%"
cd /d "%ROOT%"
if "%PROBE_RC%"=="0" goto :mysql_ok

echo       MySQL is not reachable; trying to start its Windows service...
call :start_mysql
if errorlevel 1 goto :mysql_down
set "MYSQL_WAIT=0"
:wait_mysql
cd /d "%BACKEND%"
"%VENV_PY%" -m scripts.bootstrap_db probe >nul 2>nul
set "PROBE_RC=%ERRORLEVEL%"
cd /d "%ROOT%"
if "%PROBE_RC%"=="0" goto :mysql_ok
set /a MYSQL_WAIT+=1
if %MYSQL_WAIT% GEQ 15 goto :mysql_down
ping -n 2 127.0.0.1 >nul
goto :wait_mysql

:mysql_ok

rem ---------- 5. .env, database and application account ----------
echo [4/6] Checking database configuration...
cd /d "%BACKEND%"
"%VENV_PY%" -m scripts.bootstrap_db check
set "DB_RC=%ERRORLEVEL%"
cd /d "%ROOT%"
if "%DB_RC%"=="0" goto :db_ready
if "%DB_RC%"=="5" goto :db_fix_jwt
if "%DB_RC%"=="3" goto :mysql_down
if "%DB_RC%"=="2" goto :db_need_root
goto :db_failed

:db_fix_jwt
echo       Generating a secure JWT secret...
cd /d "%BACKEND%"
"%VENV_PY%" -m scripts.bootstrap_db ensure
set "DB_RC=%ERRORLEVEL%"
cd /d "%ROOT%"
if not "%DB_RC%"=="0" goto :db_failed
goto :db_ready

:db_need_root
echo.
echo The database or the application account is not ready on this machine.
echo Enter your local MySQL root account so the launcher can create:
echo   - database : smart_study_room
echo   - app user : study_app (the application never runs as root)
echo.
echo The password is used once and is not written to any file. Input is visible.
echo.
set "ROOT_USER=root"
set "ROOT_USER_INPUT="
set /p "ROOT_USER_INPUT=MySQL root user [root]: "
if not "%ROOT_USER_INPUT%"=="" set "ROOT_USER=%ROOT_USER_INPUT%"
set "MYSQL_ROOT_PASSWORD="
set /p "MYSQL_ROOT_PASSWORD=MySQL root password: "
echo.
echo       Creating database and application account...
cd /d "%BACKEND%"
"%VENV_PY%" -m scripts.bootstrap_db ensure --root-user "%ROOT_USER%"
set "DB_RC=%ERRORLEVEL%"
cd /d "%ROOT%"
if not "%DB_RC%"=="0" goto :db_failed

:db_ready
rem Do not leak the MySQL root password into the backend/frontend windows.
set "MYSQL_ROOT_PASSWORD="
set "ROOT_USER="
set "ROOT_USER_INPUT="

rem ---------- 6. Migrations and seed data ----------
echo [5/6] Applying database migrations...
cd /d "%BACKEND%"
"%VENV_PY%" -m alembic upgrade head
set "ALEMBIC_RC=%ERRORLEVEL%"
if not "%ALEMBIC_RC%"=="0" goto :migration_failed

echo       Seeding demo accounts and data (idempotent)...
set "PYTHONIOENCODING=utf-8"
set "PYTHONUTF8=1"
"%VENV_PY%" -m scripts.seed
if errorlevel 1 goto :seed_failed
"%VENV_PY%" -m scripts.seed_demo
if errorlevel 1 goto :seed_failed
cd /d "%ROOT%"

rem ---------- 7. Frontend dependencies ----------
echo [6/6] Preparing frontend...
if exist "%FRONTEND%\node_modules\vite\bin\vite.js" goto :frontend_ready
echo       Installing frontend dependencies (first run may take a few minutes)...
cd /d "%FRONTEND%"
call npm install --no-audit --no-fund
set "NPM_RC=%ERRORLEVEL%"
cd /d "%ROOT%"
if not "%NPM_RC%"=="0" goto :npm_failed

:frontend_ready

rem ---------- 8. Start backend and frontend ----------
echo.
echo Starting services...
call :port_in_use 8000
if not errorlevel 1 goto :backend_started
pushd "%BACKEND%"
start "SSR Backend" cmd /k ".venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000"
popd
echo       Backend window opened: http://127.0.0.1:8000
:backend_started

call :port_in_use 5173
if not errorlevel 1 goto :frontend_started
pushd "%FRONTEND%"
start "SSR Frontend" cmd /k "npm run dev"
popd
echo       Frontend window opened: http://127.0.0.1:5173
:frontend_started

echo.
echo Waiting for the backend health check...
set "HAS_CURL=0"
where curl >nul 2>nul
if not errorlevel 1 set "HAS_CURL=1"
set "TRIES=0"
:wait_backend
set /a TRIES+=1
if "%HAS_CURL%"=="1" goto :check_backend_http
call :port_in_use 8000
if not errorlevel 1 goto :backend_up
goto :wait_backend_next
:check_backend_http
curl -s -f -o nul http://127.0.0.1:8000/health >nul 2>nul
if not errorlevel 1 goto :backend_up
:wait_backend_next
if %TRIES% GEQ 60 goto :backend_timeout
ping -n 2 127.0.0.1 >nul
goto :wait_backend

:backend_timeout
echo [warn] Backend did not answer http://127.0.0.1:8000/health within 60s.
echo        Check the "SSR Backend" window for errors.
goto :wait_frontend_start

:backend_up
echo       Backend is up.

:wait_frontend_start
set "TRIES=0"
:wait_frontend
set /a TRIES+=1
call :port_in_use 5173
if not errorlevel 1 goto :frontend_up
if %TRIES% GEQ 60 goto :frontend_timeout
ping -n 2 127.0.0.1 >nul
goto :wait_frontend

:frontend_timeout
echo [warn] Frontend did not start on port 5173 within 60s.
echo        Check the "SSR Frontend" window for errors.
goto :done

:frontend_up
echo       Frontend is up.
if "%NO_BROWSER%"=="1" goto :done
start "" http://127.0.0.1:5173

:done
echo.
echo ============================================================
echo   System is ready
echo   Frontend : http://127.0.0.1:5173
echo   API docs : http://127.0.0.1:8000/docs
echo.
echo   Demo accounts:
echo     student / student123   (student)
echo     admin   / admin123     (administrator)
echo.
echo   Close the "SSR Backend" and "SSR Frontend" windows to stop.
echo ============================================================
echo.
timeout /t 6 >nul 2>nul
if errorlevel 1 ping -n 7 127.0.0.1 >nul
exit /b 0


rem ============================================================
rem  Subroutines
rem ============================================================

:install_backend_deps
cd /d "%BACKEND%"
set "REQ_HASH="
"%VENV_PY%" -c "import hashlib,pathlib;print(hashlib.sha256(pathlib.Path('requirements.txt').read_bytes()).hexdigest())" > ".venv\.req-hash.tmp" 2>nul
if errorlevel 1 goto :ibd_install
set /p REQ_HASH=<".venv\.req-hash.tmp"
del ".venv\.req-hash.tmp" >nul 2>nul
set "SAVED_HASH="
if exist ".venv\.requirements.sha256" set /p SAVED_HASH=<".venv\.requirements.sha256"
if not defined REQ_HASH goto :ibd_install
if "%REQ_HASH%"=="%SAVED_HASH%" goto :ibd_ok

:ibd_install
echo [2/6] Installing backend dependencies (first run may take a few minutes)...
"%VENV_PY%" -m pip install -r requirements.txt --disable-pip-version-check --no-input
if errorlevel 1 goto :ibd_fail
if defined REQ_HASH > ".venv\.requirements.sha256" echo %REQ_HASH%
cd /d "%ROOT%"
exit /b 0

:ibd_ok
rem Dependency list is unchanged, but the venv may have been damaged by hand.
"%VENV_PY%" -c "import fastapi, pymysql, sqlalchemy, alembic, uvicorn, pydantic_settings" >nul 2>nul
if errorlevel 1 goto :ibd_install
cd /d "%ROOT%"
exit /b 0

:ibd_fail
cd /d "%ROOT%"
exit /b 1

:start_mysql
set "MYSQL_SERVICE="
for /f "tokens=2" %%s in ('sc query state^= all ^| findstr /i "SERVICE_NAME: MySQL"') do if not defined MYSQL_SERVICE set "MYSQL_SERVICE=%%s"
if not defined MYSQL_SERVICE exit /b 1
sc query "%MYSQL_SERVICE%" | findstr /i "RUNNING" >nul
if not errorlevel 1 exit /b 0
echo       Starting MySQL service "%MYSQL_SERVICE%"...
net start "%MYSQL_SERVICE%" >nul 2>&1
if errorlevel 1 exit /b 1
exit /b 0

:port_in_use
netstat -ano | findstr /r /c:":%~1 " | findstr /i "LISTENING" >nul
if errorlevel 1 exit /b 1
exit /b 0


rem ============================================================
rem  Error handlers
rem ============================================================

:not_project
echo [ERROR] backend\requirements.txt or frontend\package.json was not found.
echo         Put start.bat in the repository root and run it from there.
goto :halt

:no_python
echo [ERROR] Python 3.11+ was not found.
echo         Install it from https://www.python.org/downloads/
echo         and enable "Add python.exe to PATH" during installation.
goto :halt

:no_node
echo [ERROR] Node.js 18+ and npm were not found.
echo         Install the LTS version from https://nodejs.org/
goto :halt

:old_node
echo [ERROR] Node.js %NODE_MAJOR%.x is too old; version 18 or newer is required.
echo         Install the LTS version from https://nodejs.org/
goto :halt

:venv_failed
echo [ERROR] Failed to create backend\.venv.
echo         Check that Python can create virtual environments on this machine.
goto :halt

:pip_failed
echo [ERROR] Failed to install backend dependencies.
echo         Check the network connection and run start.bat again.
goto :halt

:mysql_down
echo [ERROR] MySQL is not reachable.
echo         1. Install MySQL 8.x: https://dev.mysql.com/downloads/installer/
echo         2. Start the MySQL service: services.msc, or "net start MySQLxx"
echo            from an administrator command prompt.
echo         3. Make sure the host and port in backend\.env match the server.
echo.
echo         This launcher can create the database, the app account, the
echo         schema and the demo data, but it cannot install the MySQL
echo         server program itself.
goto :halt

:db_failed
echo [ERROR] Database setup failed.
echo         Check backend\.env, the MySQL root credentials and the backend
echo         output above, then run start.bat again.
goto :halt

:migration_failed
cd /d "%ROOT%"
echo [ERROR] Alembic migration failed.
echo         Check the backend output above. If the application account has
echo         insufficient privileges, re-run start.bat and let it recreate
echo         the account with the MySQL root password.
goto :halt

:seed_failed
cd /d "%ROOT%"
echo [ERROR] Seeding demo data failed.
echo         Check the backend output above and run start.bat again.
goto :halt

:npm_failed
echo [ERROR] Failed to install frontend dependencies.
echo         Check the network connection, then run "npm install" in frontend\
echo         or run start.bat again.
goto :halt

:halt
echo.
echo Launcher stopped. Press any key to close this window.
pause >nul
exit /b 1

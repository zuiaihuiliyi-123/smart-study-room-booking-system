@echo off
rem ASCII only: Windows cmd may parse .bat with the OEM code page, so keep messages in English.
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo [ERROR] Virtual environment not found: .venv
    echo         Run these commands first:
    echo             python -m venv .venv
    echo             .venv\Scripts\python.exe -m pip install -r requirements.txt
    pause
    exit /b 1
)

if not exist ".env" (
    echo [WARN] .env not found. Copy .env.example to .env and fill in DATABASE_URL.
    echo.
)

echo [INFO] Starting backend: http://127.0.0.1:8000
echo [INFO] API docs:       http://127.0.0.1:8000/docs
echo [INFO] Press Ctrl+C to stop.
echo.

".venv\Scripts\python.exe" -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

if errorlevel 1 (
    echo.
    echo [ERROR] Backend exited abnormally.
    echo         Check: MySQL service running, .env password, and "alembic upgrade head" already done.
    pause
)

endlocal

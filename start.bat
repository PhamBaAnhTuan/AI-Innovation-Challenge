@echo off
setlocal
cd /d "%~dp0"

where node.exe >nul 2>nul
if errorlevel 1 (
    echo ERROR: Node.js is not installed or is not available in PATH.
    pause
    exit /b 1
)

where npm.cmd >nul 2>nul
if errorlevel 1 (
    echo ERROR: npm is not available in PATH.
    pause
    exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
    where python.exe >nul 2>nul
    if errorlevel 1 (
        echo ERROR: Python is not installed or is not available in PATH.
        echo Create a virtual environment and install requirements.txt first.
        pause
        exit /b 1
    )
)

if not exist "node_modules\vite" (
    echo ERROR: Frontend dependencies are missing.
    echo Run npm install in this folder first.
    pause
    exit /b 1
)

if not exist ".env" (
    echo WARNING: .env was not found. Configure DATABASE_URL and admin credentials first.
)

if exist ".venv\Scripts\python.exe" (
    start "AI Challenge - FastAPI" /b ".venv\Scripts\python.exe" -m uvicorn server:app --reload
) else (
    start "AI Challenge - FastAPI" /b python.exe -m uvicorn server:app --reload
)

echo Landing page: http://127.0.0.1:5173
echo Admin page:   http://127.0.0.1:5173/admin
echo FastAPI and Vite logs will appear in this VS Code terminal.
echo Press Ctrl+C here to stop the services.
echo.

call npm.cmd run dev -- --host 127.0.0.1

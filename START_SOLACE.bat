@echo off
setlocal EnableExtensions
title Solace Enterprise Core
cd /d "%~dp0"

echo ============================================
echo   Solace Enterprise Core
echo ============================================
echo.

if exist "scripts\set_env.local.bat" (
    call "scripts\set_env.local.bat"
)
if "%SOLACE_MASTER_KEY%"=="" (
    echo ERROR: SOLACE_MASTER_KEY not set.
    echo Create scripts\set_env.local.bat with your master key.
    pause
    exit /b 1
)

if not exist "backend\venv\Scripts\python.exe" (
    echo Creating Python virtual environment...
    python -m venv backend\venv
    if errorlevel 1 (
        echo ERROR: Python 3.11+ required on PATH.
        pause
        exit /b 1
    )
)

echo Installing backend dependencies...
"backend\venv\Scripts\python.exe" -m pip install -q -r backend\requirements.txt
if errorlevel 1 (
    echo ERROR: Backend install failed.
    pause
    exit /b 1
)

if not exist "backend\data\bootstrap.enc" (
    echo NOTE: First run - use http://localhost:5173/setup after start.
    echo.
)

where npm >nul 2>&1
if errorlevel 1 (
    echo ERROR: Node.js/npm required for the UI.
    pause
    exit /b 1
)

if not exist "frontend\node_modules" (
    echo Installing frontend dependencies...
    pushd frontend
    call npm install
    popd
    if errorlevel 1 (
        echo ERROR: Frontend install failed.
        pause
        exit /b 1
    )
)

set "ROOT=%~dp0"
set "ROOT=%ROOT:~0,-1%"

echo Starting API http://127.0.0.1:8080 ...
start "Solace API" cmd /k "cd /d "%ROOT%\backend" && set SOLACE_MASTER_KEY=%SOLACE_MASTER_KEY% && "%ROOT%\backend\venv\Scripts\uvicorn.exe" app.main:app --host 127.0.0.1 --port 8080 --app-dir ."

timeout /t 3 /nobreak >nul

echo Starting UI http://localhost:5173 ...
start "Solace UI" cmd /k "cd /d "%ROOT%\frontend" && npm run dev"

timeout /t 4 /nobreak >nul
start "" "http://localhost:5173"

echo.
echo   API:  http://127.0.0.1:8080/health
echo   UI:   http://localhost:5173
echo   Close Solace API / Solace UI windows to stop.
echo.
pause

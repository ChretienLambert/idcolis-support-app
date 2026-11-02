@echo off
setlocal enabledelayedexpansion

echo.
echo ===============================================
echo ID Colis Support App - Launcher (Script)
echo ===============================================
echo.

REM Check if venv exists
if not exist .venv (
    echo ERROR: Virtual environment not found!
    echo Please run 'setup.bat' first to set up the environment.
    pause
    exit /b 1
)

echo Activating virtual environment...
call .venv\Scripts\activate.bat

echo.
echo Starting ID Colis Support App...
echo.
echo Backend: http://127.0.0.1:8000
echo Frontend: http://localhost:8501
echo.
echo Press Ctrl+C to stop the application
echo.

REM Start backend in background
echo Starting backend service...
start "ID Colis Backend" cmd /k "cd /d "%~dp0" && .venv\Scripts\python.exe -m backend.serve"

REM Give backend time to start
timeout /t 2 /nobreak

REM Start frontend
echo.
echo Starting frontend...
start "ID Colis Frontend" cmd /k "cd /d "%~dp0" && .venv\Scripts\python.exe -m streamlit run app.py --server.port 8501"

pause



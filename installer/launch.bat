@echo off
setlocal enabledelayedexpansion
set "APP_DIR=%~dp0"

echo ===============================================
echo ID Colis Support App
echo ===============================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo.
    echo Please install Python 3.12+ from https://www.python.org/
    echo Make sure to check "Add Python to PATH" during installation
    echo.
    pause
    exit /b 1
)

echo Python found:
python --version
echo.

REM Check if venv exists, if not create it
if not exist "%APP_DIR%.venv" (
    echo Creating virtual environment...
    python -m venv "%APP_DIR%.venv"
    if errorlevel 1 (
        echo ERROR: Failed to create virtual environment
        pause
        exit /b 1
    )
    echo Virtual environment created
    echo.
)

REM Activate virtual environment
call "%APP_DIR%.venv\Scripts\activate.bat"

REM Install dependencies
echo Installing dependencies...
pip install --upgrade pip
pip install -r "%APP_DIR%requirements.txt"
if errorlevel 1 (
    echo ERROR: Failed to install dependencies
    pause
    exit /b 1
)
echo Dependencies installed
echo.

REM Start backend in background
echo Starting backend...
start /B python -m backend.serve
echo Backend starting on http://127.0.0.1:8000
echo.

REM Wait for backend to be ready
echo Waiting for backend to start...
timeout /t 5 /nobreak >nul

REM Start frontend
echo Starting frontend...
python -m streamlit run "%APP_DIR%app.py" --server.port 8501



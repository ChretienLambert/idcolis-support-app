@echo off
setlocal enabledelayedexpansion

echo.
echo ===============================================
echo ID Colis Support App - Setup (Script)
echo ===============================================
echo.

REM Check Python installation
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.12+ from https://www.python.org/
    pause
    exit /b 1
)

echo Python found: 
python --version

echo.
echo Creating virtual environment...
py -3.14 -m venv .venv

echo.
echo Activating virtual environment...
call .venv\Scripts\activate.bat

echo.
echo Upgrading pip and wheel...
python -m pip install --upgrade pip wheel

echo.
echo Installing project dependencies...
python -m pip install -r requirements.txt

echo.
echo ===============================================
echo Setup complete!
echo ===============================================
echo.
echo To activate the virtual environment in the future, run:
echo   .venv\Scripts\activate.bat
echo.
echo To launch the app, run:
echo   launch.bat
echo.
pause



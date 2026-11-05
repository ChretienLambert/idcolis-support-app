@echo off
setlocal
title ID Colis Support App
cd /d "%~dp0"
echo Starting ID Colis Support App...
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0run_presentation.ps1"
if errorlevel 1 (
    echo Launcher failed.
    pause
    exit /b 1
)
echo Run launch.bat again any time to restart cleanly.
exit /b 0

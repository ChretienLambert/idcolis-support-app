@echo off
setlocal enabledelayedexpansion
set "INSTALLER_DIR=%~dp0"
set "ROOT=%INSTALLER_DIR%.."

echo.
echo ===============================================
echo Building ID Colis Support App Installer
echo ===============================================
echo.

echo Building installer with Inno Setup...
echo.

REM Check if Inno Setup is installed (multiple possible locations)
set "INNO_PATH="
if exist "C:\Program Files (x86)\Inno Setup 6\iscc.exe" set "INNO_PATH=C:\Program Files (x86)\Inno Setup 6\iscc.exe"
if not defined INNO_PATH if exist "C:\Program Files\Inno Setup 7\iscc.exe" set "INNO_PATH=C:\Program Files\Inno Setup 7\iscc.exe"
if not defined INNO_PATH if exist "C:\Program Files (x86)\Inno Setup 7\iscc.exe" set "INNO_PATH=C:\Program Files (x86)\Inno Setup 7\iscc.exe"

if not defined INNO_PATH (
    echo ERROR: Inno Setup not found at default locations!
    echo.
    echo Please download and install Inno Setup from:
    echo https://jrsoftware.org/isdl.php
    echo.
    echo After installation, try again.
    pause
    exit /b 1
)

REM Build the installer
"%INNO_PATH%" /O"%INSTALLER_DIR%dist\installer" /F"IDColisSetup" "%INSTALLER_DIR%IDColisSetup.iss"
if errorlevel 1 (
    echo ERROR: Inno Setup build failed!
    pause
    exit /b 1
)

echo.
echo ===============================================
echo Build Complete!
echo ===============================================
echo.
echo Installer location: %INSTALLER_DIR%dist\installer\IDColisSetup.exe
echo.
echo The installer is ready to distribute!
echo.
pause



@echo off
setlocal enabledelayedexpansion
set "ROOT=%~dp0"
set "INNO_PATH="
if exist "C:\Program Files (x86)\Inno Setup 6\iscc.exe" set "INNO_PATH=C:\Program Files (x86)\Inno Setup 6\iscc.exe"
if not defined INNO_PATH if exist "C:\Program Files\Inno Setup 7\iscc.exe" set "INNO_PATH=C:\Program Files\Inno Setup 7\iscc.exe"
if not defined INNO_PATH if exist "C:\Program Files (x86)\Inno Setup 7\iscc.exe" set "INNO_PATH=C:\Program Files (x86)\Inno Setup 7\iscc.exe"

echo.
echo ===============================================
echo Building ID Colis Support App Inno Installer
echo ===============================================
echo.

if not exist "%ROOT%dist\exe\ID ColisApp.exe" (
    echo ERROR: Application executable not found.
    echo Please place the application binary at dist\exe\IDColisApp.exe or update IDColisSetup.iss to point to your executable.
    pause
    exit /b 1
)

if not defined INNO_PATH (
    echo ERROR: Inno Setup not found at the default locations!
    echo Please download and install Inno Setup 6 or 7 from:
    echo https://jrsoftware.org/isdl.php
    pause
    exit /b 1
)

cd /d "%ROOT%"
if not exist "%ROOT%dist\installer" mkdir "%ROOT%dist\installer"
"%INNO_PATH%" /O"%ROOT%dist\installer" /F"IDColisSetup" "%ROOT%IDColisSetup.iss"
if errorlevel 1 (
    echo ERROR: Inno Setup build failed!
    pause
    exit /b 1
)

echo.
echo ===============================================
echo Inno Setup installer build complete!
echo ===============================================
echo.
echo Installer location: %ROOT%dist\installer\IDColisSetup.exe
echo.
pause



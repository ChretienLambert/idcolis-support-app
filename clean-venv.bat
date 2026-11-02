@echo off
setlocal enabledelayedexpansion

echo Removing virtual environment and cache (script)...

REM Remove virtual environment
if exist .venv (
    echo Removing .venv...
    rmdir /s /q .venv
)

REM Remove build directories
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist

REM Remove Python cache
for /d /r . %%d in (__pycache__) do (
    if exist "%%d" rmdir /s /q "%%d"
)

for /r . %%f in (*.pyc) do (
    if exist "%%f" del /q "%%f"
)

REM Remove egg-info
for /d %%d in (*.egg-info) do (
    if exist "%%d" rmdir /s /q "%%d"
)

echo Cleanup complete!



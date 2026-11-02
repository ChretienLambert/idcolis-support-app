@echo off
setlocal enabledelayedexpansion

echo Cleaning build artifacts and cache (script)...

REM Remove PyInstaller build directories
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist IDColisSetup.spec del /q IDColisSetup.spec

REM Remove Python cache
for /d /r . %%d in (__pycache__) do @if exist "%%d" rmdir /s /q "%%d"
for /r . %%f in (*.pyc) do @if exist "%%f" del /q "%%f"
for /r . %%f in (*.pyo) do @if exist "%%f" del /q "%%f"

REM Remove egg-info
if exist ID Colis_it_support_engine.egg-info rmdir /s /q ID Colis_it_support_engine.egg-info

echo Cleanup complete!



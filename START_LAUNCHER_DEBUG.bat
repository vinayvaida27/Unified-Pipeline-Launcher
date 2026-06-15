@echo off
:: ============================================================
:: Unified Streamlit Launcher (debug console)
:: Use START_LAUNCHER.lnk or START_LAUNCHER.vbs for normal no-console launches.
:: ============================================================

set ROOT=%~dp0
set EXE=%ROOT%launcher.exe
set PYTHON=%ROOT%runtime\python.exe
set CONFIG=%ROOT%config\launcher_config.json

if exist "%EXE%" (
    "%EXE%"
    exit /b %ERRORLEVEL%
)

if not exist "%PYTHON%" (
    echo.
    echo  ERROR: Python runtime not found.
    echo  Ask your administrator to run:
    echo    scripts\deploy_network.ps1
    echo.
    pause
    exit /b 1
)

:: Debug mode intentionally uses python.exe so errors remain visible.
"%PYTHON%" -m launcher --config "%CONFIG%"

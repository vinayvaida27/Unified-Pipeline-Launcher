@echo off
:: ============================================================
:: Unified Streamlit Launcher (debug console)
:: Use START_LAUNCHER.vbs for normal no-console launches.
:: ============================================================

set ROOT=%~dp0
set PYTHON=%ROOT%runtime\python.exe
set CONFIG=%ROOT%config\launcher_config.json

if not exist "%PYTHON%" (
    echo.
    echo  ERROR: Python runtime not found.
    echo  Ask your administrator to run:
    echo    scripts\deploy_network.ps1
    echo.
    pause
    exit /b 1
)

:: Run launcher directly using the bundled runtime -- no venv needed.
start "" /B "%PYTHON%" -m launcher --config "%CONFIG%"

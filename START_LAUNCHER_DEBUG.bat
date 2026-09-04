@echo off
:: ============================================================
:: Unified Pipeline Launcher (debug console)
:: Use START_LAUNCHER.lnk or START_LAUNCHER.vbs for normal no-console launches.
:: ============================================================

for %%I in ("%~dp0.") do set "ROOT=%%~fI"
set "EXE=%ROOT%\launcher.exe"
set "SRC=%ROOT%\src"
if not exist "%SRC%" set "SRC=%ROOT%"
set "PYTHON=%SRC%\runtime\python.exe"
set "CONFIG=%SRC%\config\launcher_config.json"

if exist "%EXE%" (
    "%EXE%"
    exit /b %ERRORLEVEL%
)

if not exist "%PYTHON%" (
    echo.
    echo  ERROR: Python runtime not found.
    echo  Ask your administrator to run:
    echo    src\scripts\deploy_network.ps1
    echo.
    pause
    exit /b 1
)

:: Debug mode intentionally uses python.exe so errors remain visible.
pushd "%SRC%"
"%PYTHON%" -m launcher --config "%CONFIG%"
set EXITCODE=%ERRORLEVEL%
popd
exit /b %EXITCODE%

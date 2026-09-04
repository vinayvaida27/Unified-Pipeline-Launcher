@echo off
setlocal
title Unified Pipeline Launcher - Debug

for %%I in ("%~dp0.") do set "ROOT=%%~fI"
set "SRC=%ROOT%\src"
if not exist "%SRC%" set "SRC=%ROOT%"
set "PYTHON=%SRC%\runtime\python.exe"
set "CONFIG=%SRC%\config\launcher_config.json"

if not exist "%PYTHON%" (
    echo.
    echo ERROR: Bundled Python runtime not found:
    echo   %PYTHON%
    echo.
    echo Run INSTALL.bat or src\scripts\deploy_network.ps1 first.
    echo.
    pause
    exit /b 1
)

if not exist "%CONFIG%" (
    echo.
    echo ERROR: Launcher configuration not found:
    echo   %CONFIG%
    echo.
    pause
    exit /b 1
)

set "PYTHONHOME="
set "PYTHONPATH="
set "PYTHONSTARTUP="
set "PYTHONUSERBASE="
set "PYTHONNOUSERSITE=1"

pushd "%SRC%"

echo.
echo ============================================================
echo   Unified Pipeline Launcher - Debug Start
echo ============================================================
echo Root   : %ROOT%
echo Source : %SRC%
echo Python : %PYTHON%
echo Config : %CONFIG%
echo.

"%PYTHON%" -I -c "import encodings; from PySide6.QtWidgets import QApplication; import streamlit; print('Runtime validation: OK')"
if errorlevel 1 (
    echo.
    echo ERROR: Bundled runtime validation failed.
    popd
    pause
    exit /b 1
)

echo Starting launcher...
echo.
"%PYTHON%" -I -m launcher --config "%CONFIG%" --no-local-cache
set "EXITCODE=%ERRORLEVEL%"

popd

echo.
if not "%EXITCODE%"=="0" (
    echo Launcher exited with code %EXITCODE%.
    pause
)
exit /b %EXITCODE%

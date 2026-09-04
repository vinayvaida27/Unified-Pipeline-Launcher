@echo off
setlocal

for %%I in ("%~dp0.") do set "ROOT=%%~fI"
set "SRC=%ROOT%\src"
if not exist "%SRC%" set "SRC=%ROOT%"
set "PYTHON=%SRC%\runtime\python.exe"
set "PYTHONW=%SRC%\runtime\pythonw.exe"
set "CONFIG=%SRC%\config\launcher_config.json"

if not exist "%PYTHON%" (
    echo ERROR: Bundled Python runtime not found:
    echo   %PYTHON%
    echo Run INSTALL.bat or src\scripts\deploy_network.ps1 first.
    pause
    exit /b 1
)

if not exist "%PYTHONW%" (
    echo ERROR: Bundled pythonw.exe not found:
    echo   %PYTHONW%
    echo Run INSTALL.bat or src\scripts\deploy_network.ps1 first.
    pause
    exit /b 1
)

if not exist "%CONFIG%" (
    echo ERROR: Launcher configuration not found:
    echo   %CONFIG%
    pause
    exit /b 1
)

set "PYTHONHOME="
set "PYTHONPATH="
set "PYTHONSTARTUP="
set "PYTHONUSERBASE="
set "PYTHONNOUSERSITE=1"

pushd "%SRC%"
"%PYTHON%" -I -c "import encodings; from PySide6.QtWidgets import QApplication; import streamlit" >nul 2>&1
if errorlevel 1 (
    echo ERROR: Bundled runtime validation failed.
    echo Run START_LAUNCHER_DEBUG.bat for details.
    popd
    pause
    exit /b 1
)

start "" "%PYTHONW%" -I -m launcher --config "%CONFIG%" --no-local-cache
set "EXITCODE=%ERRORLEVEL%"
popd
exit /b %EXITCODE%

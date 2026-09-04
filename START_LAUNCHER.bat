@echo off
setlocal

set "SILENT=0"
if /I "%~1"=="--silent" set "SILENT=1"

for %%I in ("%~dp0.") do set "ROOT=%%~fI"
set "SRC=%ROOT%\src"
if not exist "%SRC%" set "SRC=%ROOT%"
set "PYTHON=%SRC%\runtime\python.exe"
set "PYTHONW=%SRC%\runtime\pythonw.exe"
set "CONFIG=%SRC%\config\launcher_config.json"

if not exist "%PYTHON%" (
    echo ERROR: Bundled Python runtime not found:
    echo   %PYTHON%
    echo Run src\scripts\deploy_network.ps1 first.
    if "%SILENT%"=="0" pause
    exit /b 1
)

if not exist "%PYTHONW%" (
    echo ERROR: Bundled pythonw.exe not found:
    echo   %PYTHONW%
    echo Run src\scripts\deploy_network.ps1 first.
    if "%SILENT%"=="0" pause
    exit /b 1
)

if not exist "%CONFIG%" (
    echo ERROR: Launcher configuration not found:
    echo   %CONFIG%
    if "%SILENT%"=="0" pause
    exit /b 1
)

set "PYTHONHOME="
set "PYTHONPATH="
set "PYTHONSTARTUP="
set "PYTHONUSERBASE="
set "PYTHONNOUSERSITE=1"

rem pushd handles both mapped-drive and UNC source paths.
pushd "%SRC%"
if errorlevel 1 (
    echo ERROR: Could not enter launcher source directory:
    echo   %SRC%
    if "%SILENT%"=="0" pause
    exit /b 1
)

"%PYTHON%" -I -c "import encodings; from PySide6.QtWidgets import QApplication; import streamlit" >nul 2>&1
if errorlevel 1 (
    echo ERROR: Bundled runtime validation failed.
    echo Run START_LAUNCHER_DEBUG.bat for details.
    popd
    if "%SILENT%"=="0" pause
    exit /b 1
)

"%PYTHON%" -c "import launcher" >nul 2>&1
if errorlevel 1 (
    echo ERROR: Launcher source package could not be imported.
    echo Run START_LAUNCHER_DEBUG.bat for details.
    popd
    if "%SILENT%"=="0" pause
    exit /b 1
)

start "" "%PYTHONW%" -m launcher --config "%CONFIG%" --no-local-cache
set "EXITCODE=%ERRORLEVEL%"
popd

if not "%EXITCODE%"=="0" (
    echo ERROR: Launcher process could not be started. Exit code: %EXITCODE%
    if "%SILENT%"=="0" pause
)
exit /b %EXITCODE%

@echo off
setlocal

for %%I in ("%~dp0.") do set "ROOT=%%~fI"
set "SRC=%ROOT%\src"
if not exist "%SRC%" set "SRC=%ROOT%"
set "PYTHONW=%SRC%\runtime\pythonw.exe"
set "CONFIG=%SRC%\config\launcher_config.json"

if not exist "%PYTHONW%" (
    echo ERROR: Bundled Python runtime not found:
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
start "" "%PYTHONW%" -I -m launcher --config "%CONFIG%" --no-local-cache
set "EXITCODE=%ERRORLEVEL%"
popd
exit /b %EXITCODE%

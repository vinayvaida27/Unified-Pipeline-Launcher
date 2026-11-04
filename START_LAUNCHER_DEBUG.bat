@echo off
setlocal EnableExtensions

:: ============================================================
:: Unified Streamlit Launcher - DEBUG CONSOLE
:: Use this first. It keeps errors visible.
:: ============================================================

set "ROOT=%~dp0"
set "EXE=%ROOT%launcher.exe"
set "SRC=%ROOT%src"
if not exist "%SRC%" set "SRC=%ROOT%"
set "PYTHON=%SRC%\runtime\python.exe"
set "PYTHONW=%SRC%\runtime\pythonw.exe"
set "CONFIG=%SRC%\config\launcher_config.json"

set "QT_LOGGING_RULES=qt.svg.warning=false;qt.svg.debug=false"

cls
echo ============================================================
echo Unified Streamlit Launcher - Debug Mode
echo ============================================================
echo ROOT   = %ROOT%
echo SRC    = %SRC%
echo PYTHON = %PYTHON%
echo CONFIG = %CONFIG%
echo.

if exist "%EXE%" (
    echo Found launcher.exe. Running compiled launcher...
    "%EXE%"
    set "EXITCODE=%ERRORLEVEL%"
    goto END
)

if not exist "%PYTHON%" (
    echo ERROR: Python runtime not found:
    echo   %PYTHON%
    echo.
    echo Fix:
    echo   Run src\scripts\update_dependencies.ps1
    echo   or src\scripts\deploy_network.ps1
    echo.
    set "EXITCODE=1"
    goto END
)

if not exist "%CONFIG%" (
    echo ERROR: Launcher config not found:
    echo   %CONFIG%
    echo.
    echo Check that you have this folder layout:
    echo   %ROOT%src\config\launcher_config.json
    echo.
    set "EXITCODE=1"
    goto END
)

echo Checking Python...
"%PYTHON%" -c "import sys; print(sys.executable); print(sys.version)"
if errorlevel 1 (
    echo.
    echo ERROR: Python runtime exists but cannot run.
    set "EXITCODE=1"
    goto END
)

echo.
echo Starting launcher module...
echo ------------------------------------------------------------
pushd "%SRC%"
"%PYTHON%" -m launcher --config "%CONFIG%"
set "EXITCODE=%ERRORLEVEL%"
popd

:END
echo.
echo ------------------------------------------------------------
echo Launcher exited with code %EXITCODE%.
echo ------------------------------------------------------------
if not "%EXITCODE%"=="0" (
    echo Copy everything above this line and send it for debugging.
)
echo.
pause
exit /b %EXITCODE%

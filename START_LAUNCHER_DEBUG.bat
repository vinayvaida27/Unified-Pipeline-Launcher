@echo off
setlocal EnableExtensions
echo ============================================================
echo Unified Streamlit Launcher - DEBUG CONSOLE
echo ============================================================
echo Starting the canonical launcher with visible diagnostics...
call "%~dp0START_LAUNCHER.bat" --debug
set "EXITCODE=%ERRORLEVEL%"
echo.
echo Launcher exited with code %EXITCODE%.
pause
exit /b %EXITCODE%

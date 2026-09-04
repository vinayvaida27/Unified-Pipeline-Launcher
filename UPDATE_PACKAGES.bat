@echo off
setlocal
title Update Unified Pipeline Launcher Packages

for %%I in ("%~dp0.") do set "ROOT=%%~fI"
set "UPDATER=%ROOT%\src\scripts\update_all_environments.ps1"

if not exist "%UPDATER%" (
    echo ERROR: Package updater was not found:
    echo   %UPDATER%
    pause
    exit /b 1
)

powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%UPDATER%" -ReleaseDir "%ROOT%"
set "EXITCODE=%ERRORLEVEL%"
echo.
if "%EXITCODE%"=="0" (
    echo Package update completed successfully.
) else (
    echo Package update completed with errors. Exit code: %EXITCODE%
)
pause
exit /b %EXITCODE%

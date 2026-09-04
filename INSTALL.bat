@echo off
setlocal
title Install Unified Pipeline Launcher

for %%I in ("%~dp0.") do set "ROOT=%%~fI"
set "DEPLOY=%ROOT%\src\scripts\deploy_network.ps1"
set "SHORTCUT=%ROOT%\START_LAUNCHER.lnk"

if not exist "%DEPLOY%" (
    echo ERROR: Installer support file was not found:
    echo   %DEPLOY%
    pause
    exit /b 1
)

echo Installing Unified Pipeline Launcher...
echo This can take several minutes the first time.
echo.

powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%DEPLOY%"
set "EXITCODE=%ERRORLEVEL%"
if not "%EXITCODE%"=="0" (
    echo.
    echo Installation failed with exit code %EXITCODE%.
    echo INSTALL.bat was kept so you can try again.
    pause
    exit /b %EXITCODE%
)

echo.
echo Installation completed successfully.
if exist "%SHORTCUT%" start "" "%SHORTCUT%"

rem This is the only temporary installer entrypoint. Reusable maintenance
rem scripts stay in src\scripts because UPDATE_PACKAGES.bat depends on them.
del /f /q "%~f0" >nul 2>&1
exit /b 0

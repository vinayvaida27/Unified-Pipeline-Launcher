@echo off
setlocal
title Install Unified Pipeline Launcher

for %%I in ("%~dp0.") do set "ROOT=%%~fI"
set "DEPLOY=%ROOT%\src\scripts\deploy_network.ps1"
set "BUILD=%ROOT%\src\scripts\BUILD_LAUNCHER_EXE.ps1"

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

if not exist "%BUILD%" (
    echo ERROR: Branded launcher build script was not found:
    echo   %BUILD%
    pause
    exit /b 1
)

echo.
echo Building the branded Windows launcher...
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%BUILD%"
set "EXITCODE=%ERRORLEVEL%"
if not "%EXITCODE%"=="0" (
    echo.
    echo Launcher build failed with exit code %EXITCODE%.
    echo INSTALL.bat was kept so you can try again.
    pause
    exit /b %EXITCODE%
)

echo.
echo Installation completed successfully.
if exist "%ROOT%\Unified-Pipeline-Launcher.exe" start "" "%ROOT%\Unified-Pipeline-Launcher.exe"
exit /b 0

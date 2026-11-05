@echo off
setlocal
title Update Unified Pipeline Launcher Packages

for %%I in ("%~dp0.") do set "ROOT=%%~fI"
set "UPDATER=%ROOT%\src\scripts\update_dependencies.ps1"
set "BUILD=%ROOT%\src\scripts\build_exe.ps1"
set "SHORTCUT_SCRIPT=%ROOT%\src\scripts\create_launcher_shortcut.ps1"

if not exist "%UPDATER%" (
    echo ERROR: Package updater was not found:
    echo   %UPDATER%
    pause
    exit /b 1
)

powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%UPDATER%" -Target launcher -ReleaseDir "%ROOT%"
set "EXITCODE=%ERRORLEVEL%"
if not "%EXITCODE%"=="0" (
    echo.
    echo Package update completed with errors. Exit code: %EXITCODE%
    pause
    exit /b %EXITCODE%
)

echo.
echo Rebuilding the branded Windows launcher...
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%BUILD%"
set "EXITCODE=%ERRORLEVEL%"
if not "%EXITCODE%"=="0" (
    echo Launcher build failed with exit code %EXITCODE%.
    pause
    exit /b %EXITCODE%
)

powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%SHORTCUT_SCRIPT%" -ReleaseDir "%ROOT%"
set "EXITCODE=%ERRORLEVEL%"
if not "%EXITCODE%"=="0" (
    echo Shortcut refresh failed with exit code %EXITCODE%.
    pause
    exit /b %EXITCODE%
)

echo.
echo Package update and launcher rebuild completed successfully.
pause
exit /b 0

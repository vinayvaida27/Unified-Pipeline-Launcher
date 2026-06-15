@echo off
:: ============================================================
:: Unified Streamlit Launcher â€” user shortcut
:: Place this .bat file anywhere (desktop, Start Menu, etc.)
:: and double-click it to open the launcher.
:: ============================================================

:: The launcher.exe lives next to this script's parent folder.
:: Adjust the path below if your release folder has a different name.
set LAUNCHER=%~dp0..\build\Unified-Streamlit-Launcher\launcher.exe

if not exist "%LAUNCHER%" (
    echo.
    echo ERROR: launcher.exe not found at:
    echo   %LAUNCHER%
    echo.
    echo Please update the path in this file or move it next to launcher.exe.
    pause
    exit /b 1
)

start "" "%LAUNCHER%"

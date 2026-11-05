@echo off
setlocal EnableExtensions
title Unified Pipeline Launcher - Repair and Diagnostics
for %%I in ("%~dp0.") do set "ROOT=%%~fI"
set "SRC=%ROOT%\src"
set "PY=%SRC%\runtime\python.exe"
set "CONF=%SRC%\config\launcher_config.json"
cd /d "%ROOT%" || goto failed
echo ============================================================
echo Unified Pipeline Launcher - Repair and Diagnostics
echo ============================================================
if not exist "%PY%" (
  echo [INFO] Bundled Python is missing. Running runtime repair...
  powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%SRC%\scripts\deploy_network.ps1"
  if errorlevel 1 goto failed
)
if not exist "%CONF%" echo [ERROR] Launcher configuration is missing: %CONF% & goto failed
echo [1/3] Validating Python and launcher imports...
cd /d "%SRC%" || goto failed
"%PY%" -c "import encodings; from PySide6 import QtWidgets; import streamlit; import launcher; print('Runtime, Qt, Streamlit, and launcher imports: OK')"
if errorlevel 1 goto failed
echo [2/3] Rebuilding Unified-Pipeline-Launcher.exe...
cd /d "%ROOT%" || goto failed
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%SRC%\scripts\BUILD_LAUNCHER_EXE.ps1" -Root "%ROOT%"
if errorlevel 1 goto failed
echo [3/3] Starting the rebuilt launcher...
start "" "%ROOT%\Unified-Pipeline-Launcher.exe"
echo Repair completed successfully.
pause
exit /b 0
:failed
echo Repair failed. Copy the error above.
pause
exit /b 1

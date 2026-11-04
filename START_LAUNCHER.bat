@echo off
setlocal DisableDelayedExpansion
set "SILENT=0"
set "DEBUG=0"
if /I "%~1"=="--silent" set "SILENT=1"
if /I "%~1"=="--debug" set "DEBUG=1"
for %%I in ("%~dp0.") do set "ROOT=%%~fI"
set "SRC=%ROOT%\src"
set "PYTHON=%SRC%\runtime\python.exe"
set "PYTHONW=%SRC%\runtime\pythonw.exe"
set "CONFIG=%SRC%\config\launcher_config.json"
set "EXE=%ROOT%\launcher.exe"
set "PYTHONHOME="
set "PYTHONPATH="
set "PYTHONSTARTUP="
set "PYTHONUSERBASE="
set "PYTHONNOUSERSITE=1"
if not exist "%PYTHON%" goto missing_runtime
if not exist "%CONFIG%" goto missing_config
pushd "%SRC%" || goto inaccessible_source
"%PYTHON%" -I -c "import encodings,os,sys; root=os.path.normcase(os.path.realpath(os.path.dirname(sys.executable))); paths=(sys.prefix,sys.exec_prefix,sys.base_prefix,encodings.__file__); raise SystemExit(0 if all(os.path.commonpath((root,os.path.normcase(os.path.realpath(p))))==root for p in paths) else 86)"
if errorlevel 1 goto invalid_runtime
"%PYTHON%" -I -c "from PySide6.QtWidgets import QApplication; import streamlit"
if errorlevel 1 goto invalid_runtime
if not exist "%EXE%" (
  "%PYTHON%" -E -s -c "import launcher"
  if errorlevel 1 goto invalid_source
)
if exist "%EXE%" (
  start "" /wait "%EXE%" --config "%CONFIG%" --no-local-cache
) else if "%DEBUG%"=="1" (
  "%PYTHON%" -E -s -m launcher --config "%CONFIG%" --no-local-cache
) else (
  start "" /wait "%PYTHONW%" -E -s -m launcher --config "%CONFIG%" --no-local-cache
)
set "EXITCODE=%ERRORLEVEL%"
popd
if "%EXITCODE%"=="0" exit /b 0
echo ERROR: Launcher exited with code %EXITCODE%.
if "%SILENT%"=="0" pause
exit /b %EXITCODE%
:missing_runtime
echo ERROR: Bundled Python runtime is missing. Run INSTALL.bat.
goto failed
:missing_config
echo ERROR: Launcher configuration is missing: %CONFIG%
goto failed
:inaccessible_source
echo ERROR: Cannot access launcher source folder: %SRC%
goto failed
:invalid_runtime
echo ERROR: Bundled runtime validation failed.
goto failed
:invalid_source
echo ERROR: Launcher source package could not be imported.
:failed
if "%SILENT%"=="0" pause
exit /b 1

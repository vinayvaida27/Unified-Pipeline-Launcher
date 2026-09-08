@echo off
setlocal DisableDelayedExpansion
rem Canonical startup for command line, hidden VBS, shortcut, and debug wrappers.
set "SILENT=0"
set "DEBUG=0"
set "ENTERED=0"
if /I "%~1"=="--silent" set "SILENT=1"
if /I "%~2"=="--silent" set "SILENT=1"
if /I "%~1"=="--debug" set "DEBUG=1"

for %%I in ("%~dp0.") do set "ROOT=%%~fI"
set "SRC=%ROOT%\src"
if not exist "%SRC%" set "SRC=%ROOT%"
set "PYTHON=%SRC%\runtime\python.exe"
set "PYTHONW=%SRC%\runtime\pythonw.exe"
set "CONFIG=%SRC%\config\launcher_config.json"
set "EXE=%ROOT%\launcher.exe"

set "PYTHONHOME="
set "PYTHONPATH="
set "PYTHONSTARTUP="
set "PYTHONUSERBASE="
set "PYTHONSAFEPATH="
set "PYTHONPLATLIBDIR="
set "PYTHONNOUSERSITE=1"

if not exist "%PYTHON%" goto missing_runtime
if not exist "%CONFIG%" goto missing_config
rem pushd creates a temporary drive mapping when invoked through a UNC path.
pushd "%SRC%"
if errorlevel 1 goto inaccessible_source
set "ENTERED=1"
if "%DEBUG%"=="0" goto validate
echo Root   : "%ROOT%"
echo Source : "%SRC%"
echo Python : "%PYTHON%"
echo Config : "%CONFIG%"

:validate
rem Imports alone can succeed while Python loads its stdlib from another install.
"%PYTHON%" -I -c "import encodings,os,sys; root=os.path.normcase(os.path.realpath(os.path.dirname(sys.executable))); paths=(sys.prefix,sys.exec_prefix,sys.base_prefix,encodings.__file__); raise SystemExit(0 if all(os.path.commonpath((root,os.path.normcase(os.path.realpath(p))))==root for p in paths) else 86)"
if errorlevel 1 goto invalid_runtime
"%PYTHON%" -I -c "from PySide6.QtWidgets import QApplication; import streamlit"
if errorlevel 1 goto invalid_runtime
if exist "%EXE%" goto frozen
if not exist "%PYTHONW%" goto missing_runtime
rem -E -s ignore inherited Python options and user packages while retaining trusted cwd.
rem Source-tree module discovery must not use -I.
"%PYTHON%" -E -s -c "import launcher"
if errorlevel 1 goto invalid_source
if "%DEBUG%"=="1" goto debug_source
rem Waiting preserves pythonw failures instead of reporting CreateProcess success.
start "" /wait "%PYTHONW%" -E -s -m launcher --config "%CONFIG%" --no-local-cache
goto finished

:debug_source
"%PYTHON%" -E -s -m launcher --config "%CONFIG%" --no-local-cache
goto finished

:frozen
start "" /wait "%EXE%" --config "%CONFIG%" --no-local-cache

:finished
set "EXITCODE=%ERRORLEVEL%"
popd
if "%EXITCODE%"=="0" exit /b 0
echo ERROR: Launcher exited with code %EXITCODE%.
echo Run START_LAUNCHER_DEBUG.bat for details.
if "%SILENT%"=="0" pause
exit /b %EXITCODE%

:missing_runtime
set "FAILURE=Bundled Python runtime is missing. Run the deployment repair script."
goto failed
:missing_config
set "FAILURE=Launcher configuration is missing. Restore the deployment configuration."
goto failed
:inaccessible_source
set "FAILURE=Cannot access the launcher source folder. Check share access and permissions."
goto failed
:invalid_runtime
set "FAILURE=Bundled runtime validation failed. Ask the administrator to repair the runtime."
goto failed
:invalid_source
set "FAILURE=Launcher source package could not be imported. Restore the launcher source."
:failed
echo ERROR: %FAILURE%
echo Python : "%PYTHON%"
echo Config : "%CONFIG%"
echo Run START_LAUNCHER_DEBUG.bat for details.
if "%ENTERED%"=="1" popd
if "%SILENT%"=="0" pause
exit /b 1

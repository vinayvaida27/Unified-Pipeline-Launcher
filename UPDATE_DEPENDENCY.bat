@echo off
setlocal
call "%~dp0UPDATE_PACKAGES.bat"
exit /b %ERRORLEVEL%

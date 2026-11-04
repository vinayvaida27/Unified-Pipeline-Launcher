@echo off
setlocal
call "%~dp0..\UPDATE_PACKAGES.bat"
exit /b %ERRORLEVEL%

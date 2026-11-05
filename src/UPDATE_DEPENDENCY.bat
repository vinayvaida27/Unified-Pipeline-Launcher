@echo off
setlocal
call "%~dp0..\update_package.bat"
exit /b %ERRORLEVEL%

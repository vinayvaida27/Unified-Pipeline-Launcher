@echo off
setlocal DisableDelayedExpansion
rem Visible diagnostic mode uses the same canonical startup implementation.
"%~dp0START_LAUNCHER.bat" --debug %*

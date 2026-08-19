@echo off
setlocal
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0PLAY_GAUNTLET.ps1" %*
endlocal

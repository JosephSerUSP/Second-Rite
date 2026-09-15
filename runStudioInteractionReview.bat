@echo off
setlocal
cd /d "%~dp0"

echo Starting Thestra Studio for OWNER INTERACTION REVIEW...
call npm start -- --project projects\hichaukitoden-game
exit /b %errorlevel%

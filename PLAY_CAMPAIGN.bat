@echo off
setlocal
cd /d "%~dp0"
echo ========================================================
echo  SECOND GATE: PALE CROSSING (Campaign Interpretation)
echo ========================================================
echo Launching full authored campaign...
echo.
node tools\editor\project-cli.js play projects\labs\pale-crossing
if errorlevel 1 (
    echo.
    echo Failed to launch campaign. Please verify Node and LÖVE are installed.
    pause
)

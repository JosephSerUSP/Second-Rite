@echo off
node tools\ci\stage-project-gates.js --output out\stage
if %ERRORLEVEL% NEQ 0 (
    echo Staging failed!
    exit /b %ERRORLEVEL%
)
"C:\Program Files\LOVE\lovec.exe" out\stage stratum3

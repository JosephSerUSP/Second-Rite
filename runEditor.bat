@echo off
setlocal
cd /d "%~dp0"

if not exist "node_modules\chokidar\package.json" (
  echo Installing editor dependencies...
  call npm ci --ignore-scripts || (
    echo Failed to install editor dependencies.
    exit /b 1
  )
)

echo Starting Thestra Studio...
call npm start -- --project "%~dp0projects\hichaukitoden-game"
set "EXIT_CODE=%ERRORLEVEL%"
if not "%EXIT_CODE%"=="0" (
  echo.
  echo Thestra Studio failed to start. Leave this window open and check the error above.
  pause
)
exit /b %EXIT_CODE%

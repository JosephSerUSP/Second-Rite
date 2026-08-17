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
call npm start
exit /b %errorlevel%

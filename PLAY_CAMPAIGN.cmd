@echo off
setlocal
rem ===========================================================================
rem  THE THIRD BELL -- experimental, machine-authored Second Gate campaign.
rem  EXPERIMENTAL / NOT CANON. Double-click this file, or run it from a shell.
rem
rem  This is a thin wrapper around the ordinary Thestra Test Play boundary:
rem    npm run project -- play projects/labs/third-bell
rem
rem  The only thing it adds is the asset mirror. The campaign Project shares
rem  Second Gate's art unchanged, so its assets/ tree is deliberately NOT
rem  committed (it would duplicate ~37 MB of binaries already in this repo).
rem  We mirror them in first, then hand off to the real Test Play lifecycle.
rem ===========================================================================

cd /d "%~dp0"

echo [third-bell] mirroring shared Second Gate assets into the campaign Project...
robocopy "assets" "projects\labs\third-bell\assets" /MIR /NFL /NDL /NJH /NJS /NP >nul
if %ERRORLEVEL% GEQ 8 (
    echo [third-bell] ERROR: asset mirror failed ^(robocopy exit %ERRORLEVEL%^).
    exit /b 1
)

echo [third-bell] launching THE THIRD BELL...
node tools\editor\project-cli.js play projects\labs\third-bell
endlocal

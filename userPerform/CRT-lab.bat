@echo off
setlocal EnableExtensions
cd /d "%~dp0.."

REM ============================================================
REM  CRT LAB - developer visual presets for #1310
REM
REM  Stages Second Gate through the same canonical Project export
REM  boundary used by the gates, then launches the real LÖVE game
REM  at WIDE with the selected CRT presentation.
REM
REM  The lab presets are experiments, not player-facing display
REM  options. Curvature is deliberately NOT included in this
REM  curated menu.
REM ============================================================

set "LOVE=C:\Program Files\LOVE\love.exe"
set "STAGE=%CD%\out\crt-lab-project"

if not exist "%LOVE%" (
    echo ERROR: LÖVE was not found at:
    echo   %LOVE%
    echo Edit this file if your installation lives elsewhere.
    pause
    exit /b 1
)

:menu
cls
echo ============================================================
echo  SECOND RITE - CRT LAB

echo  Flat-screen preset bank

echo ============================================================
echo.
echo   1. Current CRT      - existing clean control
echo   2. Heavy Beam       - stronger scanline / beam structure
echo   3. Halation         - warm glow around bright pixels
echo   4. Aperture Grille  - visible RGB phosphor triads
echo   5. Slot Mask        - staggered phosphor-slot structure
echo   6. Composite        - chroma smear + faint signal ghost
echo   7. Convergence      - RGB misregistration / fringing
echo.
echo   0. Exit
echo.
set /p "CHOICE=Choose a preset: "

if "%CHOICE%"=="1" set "MODE=crt"& set "LABEL=Current CRT"& goto launch
if "%CHOICE%"=="2" set "MODE=crt-lab:heavy-beam"& set "LABEL=Heavy Beam"& goto launch
if "%CHOICE%"=="3" set "MODE=crt-lab:halation"& set "LABEL=Halation"& goto launch
if "%CHOICE%"=="4" set "MODE=crt-lab:aperture"& set "LABEL=Aperture Grille"& goto launch
if "%CHOICE%"=="5" set "MODE=crt-lab:slot-mask"& set "LABEL=Slot Mask"& goto launch
if "%CHOICE%"=="6" set "MODE=crt-lab:composite"& set "LABEL=Composite"& goto launch
if "%CHOICE%"=="7" set "MODE=crt-lab:convergence"& set "LABEL=Convergence"& goto launch
if "%CHOICE%"=="0" exit /b 0

goto menu

:launch
echo.
echo Staging Second Gate...
if exist "%STAGE%" rmdir /s /q "%STAGE%"
node tools\ci\stage-project-gates.js --output "%STAGE%"
if errorlevel 1 (
    echo.
    echo ERROR: Project staging failed.
    pause
    exit /b 1
)

echo.
echo Launching %LABEL% ^(%MODE%^) ...
start "Second Rite - CRT Lab - %LABEL%" "%LOVE%" "%STAGE%" surface=wide output=%MODE%

echo.
echo The staged Project remains at:
echo   %STAGE%
echo.
echo Close the game, then run this launcher again to compare another preset.
echo.
pause
goto menu

@echo off
REM ============================================================
REM  G1 - VALIDATE GATE
REM  Runs the engine's data/formula validator.
REM  PASS when the output ends with:  VALIDATE OK
REM  Note: the line "[formula] error in 'os.time()'" is an
REM        EXPECTED sandbox negative-test, NOT a failure.
REM
REM  #700: the repository root is only the Thestra installation
REM  and owns no data/. The gate therefore stages the default
REM  Project through the canonical exporter boundary and
REM  validates THAT, the same way CI does.
REM ============================================================
cd /d "%~dp0.."
echo Running G1 validate...
echo.
powershell -NoProfile -ExecutionPolicy Bypass -File "tools\golden\check-validate.ps1"
echo.
echo ---------------------------------------------------------
echo G1 finished. Confirm the output ended with: VALIDATE OK
echo ---------------------------------------------------------
pause

@echo off
setlocal
rem ASH CHOIR — experimental / machine-authored / not canon.
rem The Project intentionally does not duplicate the repository's shared art.
pushd "%~dp0\..\..\.."
echo [ash-choir] preparing shared Second Gate art for this isolated Project...
robocopy "assets" "experiments\campaigns\ash-choir\assets" /MIR /NFL /NDL /NJH /NJS /NP >nul
if %ERRORLEVEL% GEQ 8 (
  echo [ash-choir] asset preparation failed ^(robocopy %ERRORLEVEL%^).
  popd
  exit /b 1
)
echo [ash-choir] launching the Ash Choir campaign...
node tools\editor\project-cli.js play experiments\campaigns\ash-choir
set RESULT=%ERRORLEVEL%
popd
exit /b %RESULT%

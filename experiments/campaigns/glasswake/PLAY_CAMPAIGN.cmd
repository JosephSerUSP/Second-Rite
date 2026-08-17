@echo off
setlocal
pushd "%~dp0\..\..\.."
call npm run project -- play experiments\campaigns\glasswake
popd

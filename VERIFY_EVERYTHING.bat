@echo off
setlocal
cd /d "%~dp0"
echo SASS HRM Enterprise - full local verification (frontend version read from package.json)
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\verify-everything.ps1"
if errorlevel 1 (
 echo.
 echo One or more checks failed. See errors above.
 pause
 exit /b 1
)
echo.
echo Verification complete.
pause

@echo off
setlocal
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "scripts\check-live-mysql.ps1"
if errorlevel 1 (
  echo Live MySQL verification FAILED. Check backend and database terminals.
  pause
  exit /b 1
)
echo Live MySQL verification succeeded.
pause

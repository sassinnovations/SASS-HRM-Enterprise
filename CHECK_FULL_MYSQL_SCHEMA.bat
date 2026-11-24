@echo off
setlocal
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\verify-full-schema.ps1"
if errorlevel 1 (
  echo Schema verification failed. Read the messages above. Do not reset existing MySQL volumes.
  pause
  exit /b 1
)
echo Schema verification passed.
pause

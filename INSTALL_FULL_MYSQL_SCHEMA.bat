@echo off
setlocal
cd /d "%~dp0"
echo WARNING: Back up and verify your existing MySQL data before schema installation.
echo This script will ask for confirmation and never drops tables, deletes records, or resets volumes.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\verify-full-schema.ps1" -Install
if errorlevel 1 (
  echo Schema installation or verification did not complete. Read the messages above.
  pause
  exit /b 1
)
echo Schema installation and verification passed.
pause

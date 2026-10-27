@echo off
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\verify-docker-full.ps1"
if errorlevel 1 (
  echo Docker full-stack verification did not pass.
  pause
  exit /b 1
)
pause

@echo off
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\start-docker-full.ps1"
if errorlevel 1 (
  echo Docker stack failed. Read the messages above.
  pause
  exit /b 1
)
pause

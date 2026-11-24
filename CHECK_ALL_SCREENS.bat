@echo off
cd /d "%~dp0"
python scripts\check-all-screens-v21.py
if errorlevel 1 (
  echo Browser check did not pass. Confirm MySQL, frontend and SASS_E2E_EMAIL/PASSWORD environment variables.
  exit /b 1
)

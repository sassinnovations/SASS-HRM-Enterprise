@echo off
cd /d "%~dp0"
echo Read-only Chrome smoke test of your running MySQL HRM.
echo In this terminal, credentials must be supplied as SASS_E2E_EMAIL and SASS_E2E_PASSWORD environment variables.
echo Install once: pip install playwright ^&^& python -m playwright install chromium
python scripts\check-browser-v20.py
if errorlevel 1 (
  echo FAIL: Review the browser smoke failure or backend connection.
  pause
  exit /b 1
)
pause

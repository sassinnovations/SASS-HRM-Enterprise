@echo off
cd /d "%~dp0"
python scripts\verify-api-version-alignment.py
if errorlevel 1 (
  echo Version alignment check FAILED.
  pause
  exit /b 1
)
echo Version alignment check passed.
pause

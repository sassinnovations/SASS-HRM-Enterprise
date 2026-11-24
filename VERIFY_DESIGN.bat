@echo off
setlocal
cd /d "%~dp0"
python scripts\verify-design-parity.py
if errorlevel 1 (
  echo Design and feature audit FAILED. Check the errors above.
  pause
  exit /b 1
)
echo SASS HRM design and feature parity checks passed.
pause

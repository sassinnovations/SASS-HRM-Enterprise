@echo off
cd /d "%~dp0"
python scripts\check-employee-services-mysql.py
if errorlevel 1 (
  echo MySQL verification FAILED. Check backend configuration and MySQL server.
  pause
  exit /b 1
)
pause

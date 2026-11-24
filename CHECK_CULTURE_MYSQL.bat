@echo off
setlocal
cd /d "%~dp0"
if exist "server\.venv\Scripts\python.exe" (
  "server\.venv\Scripts\python.exe" scripts\check-culture-mysql.py
) else (
  py -3 scripts\check-culture-mysql.py
)
if errorlevel 1 (
  echo.
  echo MySQL Culture schema check FAILED. Confirm the backend uses DB_ENGINE=mysql and is running.
  pause
  exit /b 1
)
echo.
echo Culture schema check finished. Complete API/browser/security tests before real deployment.
pause

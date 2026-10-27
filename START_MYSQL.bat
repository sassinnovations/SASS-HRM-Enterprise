@echo off
cd /d "%~dp0"
powershell -ExecutionPolicy Bypass -File "%~dp0scripts\start-mysql.ps1"
if errorlevel 1 (
  echo MySQL could not start. Check the error above.
  pause
  exit /b 1
)
echo MySQL is ready. You can now run START_HERE.bat
pause

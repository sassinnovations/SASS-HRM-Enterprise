@echo off
cd /d "%~dp0"
python "%~dp0scripts\backup-mysql.py"
if errorlevel 1 (
  echo Backup failed - see the error above.
  pause
  exit /b 1
)
pause

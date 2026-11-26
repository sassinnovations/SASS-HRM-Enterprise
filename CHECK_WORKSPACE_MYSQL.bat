@echo off
setlocal
cd /d "%~dp0server"
if not exist ".venv\Scripts\python.exe" (
  echo Backend Python environment not found. Start your existing backend as usual, then retry.
  exit /b 1
)
".venv\Scripts\python.exe" workspace_database_readiness.py --live
set "rc=%errorlevel%"
echo.
pause
exit /b %rc%

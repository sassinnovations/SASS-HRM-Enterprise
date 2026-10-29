@echo off
setlocal
cd /d "%~dp0"
echo ============================================
echo SASS HRM Enterprise v2.2 (separate local dev servers)
echo ============================================
echo Ensure SETUP_SASS_HRM.bat and CREATE_ADMIN.bat were completed, and MySQL is reachable from server/.env.
echo Opening backend and frontend in separate PowerShell windows.
echo.
start "SASS HRM Backend" powershell.exe -NoExit -ExecutionPolicy Bypass -File "%~dp0scripts\start-backend.ps1"
start "SASS HRM Frontend" powershell.exe -NoExit -ExecutionPolicy Bypass -File "%~dp0scripts\start-frontend.ps1"
echo After both terminals report ready, open http://localhost:5173
pause

@echo off
setlocal
cd /d "%~dp0"
echo ============================================
echo SASS HRM Enterprise - API and website
echo ============================================
echo MySQL must already be running. server/.env selects that database.
echo This opens the Python API and the React site in separate windows.
echo.
start "SASS HRM Backend" powershell.exe -NoExit -ExecutionPolicy Bypass -File "%~dp0scripts\start-backend.ps1"
start "SASS HRM Frontend" powershell.exe -NoExit -ExecutionPolicy Bypass -File "%~dp0scripts\start-frontend.ps1"
echo After both windows are ready, open http://localhost:5173
pause

@echo off
setlocal
cd /d "%~dp0"
echo ============================================
echo SASS HRM Enterprise v2.3 - MySQL + Docker
 echo ============================================
echo This starts the complete Docker stack: MySQL, FastAPI and React.
echo For separate Windows dev servers use START_LOCAL_DEV.bat instead.
echo.
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\start-docker-full.ps1"
if errorlevel 1 (
  echo.
  echo Startup failed. Check the errors, and run VERIFY_DOCKER_FULL.bat later.
  pause
  exit /b 1
)
echo Open http://localhost:5173
pause

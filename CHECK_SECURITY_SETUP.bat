@echo off
setlocal
cd /d "%~dp0"
echo SASS HRM MySQL credentials and JWT configuration check
where py >nul 2>nul
if %errorlevel%==0 (
  py -3 "%~dp0scripts\check-runtime-config.py"
) else (
  python "%~dp0scripts\check-runtime-config.py"
)
if errorlevel 1 (
  echo Security setup is incomplete. Use SETUP_SASS_HRM.bat for a FRESH installation ONLY.
  echo For existing databases, restore or correct your saved .env files; do not reset the MySQL volume.
) else (
  echo Credentials and JWT configuration shape verified. Passwords were NOT displayed.
)
pause

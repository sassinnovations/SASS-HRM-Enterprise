@echo off
setlocal
cd /d "%~dp0"
echo SASS HRM - safe MySQL and backend configuration diagnosis
echo The check only reads metadata and does not print secrets or employee records.
python scripts\diagnose-http-500.py --database
echo.
echo For public backend checks run:
echo python scripts\diagnose-http-500.py --url https://YOUR_BACKEND_URL
pause

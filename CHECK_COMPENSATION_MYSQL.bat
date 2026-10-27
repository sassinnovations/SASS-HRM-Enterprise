@echo off
setlocal
cd /d "%~dp0"
echo Checking real SASS HRM MySQL Compensation schema (read only)...
powershell -NoProfile -ExecutionPolicy Bypass -Command "& { $py='python'; if(Test-Path 'server\.venv\Scripts\python.exe'){$py='server\.venv\Scripts\python.exe'}; & $py 'scripts\check-compensation-mysql.py'; exit $LASTEXITCODE }"
if errorlevel 1 (echo Check failed. Ensure the MySQL service and upgraded backend are running. & pause & exit /b 1)
echo Compensation MySQL checks passed.
pause

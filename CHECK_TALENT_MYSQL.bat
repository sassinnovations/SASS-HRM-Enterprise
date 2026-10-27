@echo off
setlocal
cd /d "%~dp0"
if exist "server\.venv\Scripts\python.exe" (
 "server\.venv\Scripts\python.exe" "scripts\check-talent-mysql.py"
) else (
 python "scripts\check-talent-mysql.py"
)
if errorlevel 1 (
 echo SASS HRM MySQL Talent schema check FAILED.
 exit /b 1
)
echo SASS HRM MySQL Talent schema check PASSED.

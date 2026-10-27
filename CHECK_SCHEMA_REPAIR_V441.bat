@echo off
setlocal
cd /d "%~dp0"
echo SASS HRM v4.4.1 - read-only database schema diagnostic
python server\schema_audit.py --file-only
if errorlevel 1 (
 echo Source schema verification failed.
 pause
 exit /b 1
)
echo Now checking the existing MySQL database using Docker. No SQL writes are requested.
call CHECK_FULL_MYSQL_SCHEMA.bat

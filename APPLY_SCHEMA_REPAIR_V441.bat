@echo off
setlocal
cd /d "%~dp0"
echo =============================================================
echo SASS HRM v4.4.1 - EXPLICIT MYSQL SCHEMA REPAIR
 echo.
echo WARNING: MySQL DDL may modify tables and is not fully rollback-safe.
echo Backup the database and verify the backup BEFORE continuing.
echo Existing employee records, IDs, roles and passwords must be preserved.
echo Stop the API process before applying repairs to avoid races.
 echo.
echo Check docs\V4_4_1_SAFE_SCHEMA_REPAIR.md for instructions.
set /p CONFIRM=Type BACKUP VERIFIED to proceed to a second confirmation: 
if /I not "%CONFIRM%"=="BACKUP VERIFIED" (
 echo Cancelled. Nothing was changed by this script.
 exit /b 1
)
call INSTALL_FULL_MYSQL_SCHEMA.bat

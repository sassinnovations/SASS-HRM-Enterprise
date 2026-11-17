@echo off
setlocal
cd /d "%~dp0"
echo === SASS HRM: Expenses and Claims upgrade (237 to 241 tables) ===
python server\expense_management_test.py
if errorlevel 1 exit /b 1
python server\mysql_feature_schema_integrity.py --file-only
if errorlevel 1 exit /b 1
python server\database_feature_coverage.py --check
if errorlevel 1 exit /b 1
if /I "%~1"=="/LIVE" (
 python server\mysql_feature_schema_integrity.py --live
 if errorlevel 1 exit /b 1
 python server\check_all_mysql_connections.py --probe-tables
 if errorlevel 1 exit /b 1
) else (
 echo Live MySQL NOT checked. Run CHECK_EXPENSES_CLAIMS.bat /LIVE to verify a live database.
)
echo PASS: Offline workflow and schema verification complete. No live records modified.
exit /b 0

@echo off
setlocal
cd /d "%~dp0"
echo === SASS HRM - SASS INNOVATIONS ENTERPRISE: 263 MySQL tables ===
python server\mysql_operations21_extension_test.py
if errorlevel 1 exit /b 1
python server\mysql_feature_schema_integrity.py --file-only
if errorlevel 1 exit /b 1
python server\database_feature_coverage.py --check
if errorlevel 1 exit /b 1
if /I "%~1"=="/LIVE" (
  echo === Checking the configured live MySQL schema without modifying records ===
  python server\mysql_feature_schema_integrity.py --live
  if errorlevel 1 exit /b 1
  python server\check_all_mysql_connections.py --probe-tables
  if errorlevel 1 exit /b 1
) else (
  echo MySQL live verification NOT performed. Use /LIVE after installation.
)
echo PASS: Offline schema and inventory checks completed.
exit /b 0

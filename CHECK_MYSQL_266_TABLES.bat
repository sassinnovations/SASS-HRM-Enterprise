@echo off
setlocal
cd /d "%~dp0"
echo === SASS HRM - SASS INNOVATIONS ENTERPRISE: 266 MySQL tables ===
python server\mysql_feature_schema_integrity.py --file-only
if errorlevel 1 exit /b 1
python server\database_feature_coverage.py --check
if errorlevel 1 exit /b 1
python server\database_workflow_integration_test.py
if errorlevel 1 exit /b 1
if /I "%~1"=="/LIVE" (
  echo === Read-only MySQL schema, index, FK and table access check ===
  python server\mysql_feature_schema_integrity.py --live
  if errorlevel 1 exit /b 1
  python server\check_all_mysql_connections.py --probe-tables
  if errorlevel 1 exit /b 1
) else (
  echo Live MySQL check skipped. Use /LIVE after backup and installation.
)
echo PASS: requested offline checks completed.
exit /b 0

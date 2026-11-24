@echo off
setlocal
cd /d "%~dp0"
echo === SASS HRM: 217 to 237 MySQL tables, read-only verification ===
python server\mysql_evidence_extension_test.py
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
  echo Live MySQL was NOT checked. Pass /LIVE for read-only live verification.
)
echo PASS: MySQL schema files and additive migration agree; no data was modified.
exit /b 0

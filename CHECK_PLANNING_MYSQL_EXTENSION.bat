@echo off
setlocal
cd /d "%~dp0"
echo === SASS HRM: 20 planning/review MySQL tables (173 to 193) ===
python server\mysql_planning_extension_test.py
if errorlevel 1 exit /b 1
python server\mysql_feature_schema_integrity.py --file-only
if errorlevel 1 exit /b 1
if /I "%~1"=="/LIVE" (
  python server\mysql_feature_schema_integrity.py --live
  if errorlevel 1 exit /b 1
) else (
  echo Use /LIVE to inspect your running MySQL schema read-only.
)
echo PASS: offline schema checks finished. No database writes performed.
exit /b 0

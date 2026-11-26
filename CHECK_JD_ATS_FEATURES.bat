@echo off
setlocal
cd /d "%~dp0"
echo === SASS HRM: JD Excel import/export and ATS matching (241 to 243 tables) ===
python server\job_descriptions_test.py
if errorlevel 1 exit /b 1
python server\mysql_feature_schema_integrity.py --file-only
if errorlevel 1 exit /b 1
python server\database_feature_coverage.py --check
if errorlevel 1 exit /b 1
python scripts\verify-saritha-merge.py
if errorlevel 1 exit /b 1
if /I "%~1"=="/LIVE" (
  echo Starting read-only MySQL schema verification. Does not install migrations.
  python server\mysql_feature_schema_integrity.py --live
  if errorlevel 1 exit /b 1
  python server\check_all_mysql_connections.py --probe-tables
  if errorlevel 1 exit /b 1
) else (
  echo Live MySQL not checked. Run CHECK_JD_ATS_FEATURES.bat /LIVE after migration 20 is applied.
)
echo PASS: Selected JD/ATS workflow and schema checks.
exit /b 0

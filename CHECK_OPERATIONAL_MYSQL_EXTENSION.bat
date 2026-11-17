@echo off
setlocal
cd /d "%~dp0"
echo === SASS HRM: 20-table operational extension (153 to 173) ===
python server\mysql_operational_extension_test.py
if errorlevel 1 (
  echo ERROR: Operational schema checks failed; no database changes attempted.
  exit /b 1
)
python server\mysql_feature_schema_integrity.py --file-only
if errorlevel 1 (
  echo ERROR: Complete schema check failed; no database changes attempted.
  exit /b 1
)
if /I "%~1"=="/LIVE" (
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\verify-all-mysql-feature-schema.ps1
  if errorlevel 1 (
    echo ERROR: Live schema incomplete or MySQL connection unavailable; no changes attempted.
    exit /b 1
  )
) else (
  echo NOTE: Use /LIVE to audit the running MySQL database read-only.
)
echo PASS: schema verification completed (no database writes).
exit /b 0

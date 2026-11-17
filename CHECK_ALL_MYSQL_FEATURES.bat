@echo off
setlocal
cd /d "%~dp0"
echo === SASS HRM complete MySQL schema: offline checks ===
python "server\mysql_feature_schema_integrity.py" --file-only
if errorlevel 1 (
  echo FAILED: bundled schema files disagree. No MySQL changes made.
  pause
  exit /b 1
)
if /I "%~1"=="/LIVE" (
  echo === Checking live Docker MySQL: read-only tables, columns, indexes and FKs ===
  powershell -NoProfile -ExecutionPolicy Bypass -File "scripts\verify-all-mysql-feature-schema.ps1"
  if errorlevel 1 (
    echo FAILED: live schema incomplete or unavailable. No database changes made.
    pause
    exit /b 1
  )
) else (
  echo Live MySQL was not checked. To check: CHECK_ALL_MYSQL_FEATURES.bat /LIVE
)
echo PASS: requested schema checks completed.
pause

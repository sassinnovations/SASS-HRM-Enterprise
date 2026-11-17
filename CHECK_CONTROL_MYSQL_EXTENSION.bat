@echo off
setlocal
cd /d "%~dp0"
echo === SASS HRM: MySQL controls extension (193 to 213 tables) ===
python server\mysql_control_extension_test.py
if errorlevel 1 exit /b 1
python server\mysql_feature_schema_integrity.py --file-only
if errorlevel 1 exit /b 1
if /I "%~1"=="/LIVE" (
  python server\mysql_feature_schema_integrity.py --live
  if errorlevel 1 exit /b 1
) else (
  echo Live MySQL was NOT checked. Pass /LIVE for the read-only metadata audit.
)
echo Schema checks completed. No existing HR data was changed.
exit /b 0

@echo off
setlocal
cd /d "%~dp0"
echo Checking current 213-table schema (including legacy 15-table expansion) and 15-table advanced MySQL extension, with no data writes...
python server\mysql_advanced_extension_test.py
if errorlevel 1 (echo FAIL: advanced database verification failed & pause & exit /b 1)
python server\mysql_feature_schema_integrity.py --file-only
if errorlevel 1 (echo FAIL: full schema parity failed & pause & exit /b 1)
echo PASS: offline schema checks complete. To check live MySQL run CHECK_ALL_MYSQL_FEATURES.bat /LIVE.
pause

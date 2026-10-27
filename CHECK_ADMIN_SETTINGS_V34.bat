@echo off
setlocal
cd /d "%~dp0"
echo SASS HRM v3.4 - Settings and schema verification (synthetic database only)
python server\admin_settings_v34_test.py
if errorlevel 1 (echo Settings permissions and validation test failed.& exit /b 1)
python server\full_mysql_schema_test.py
if errorlevel 1 (echo Complete MySQL schema audit failed.& exit /b 1)
python scripts\check-page-routing.py
if errorlevel 1 (echo Settings navigation test failed.& exit /b 1)
python scripts\verify-v24-package.py --workspace
if errorlevel 1 (echo Workspace source validation failed.& exit /b 1)
echo PASS: v3.4 administration settings, permissions, database definitions and navigation.
endlocal

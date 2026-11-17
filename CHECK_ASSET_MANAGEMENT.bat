@echo off
setlocal
cd /d "%~dp0"
where python >nul 2>&1
if errorlevel 1 (echo Python 3 is required. & exit /b 1)
echo Checking Asset Management requirements, permissions, MySQL schema and page routes...
cd server
python asset_management_test.py || exit /b 1
python employee_services_v20_test.py || exit /b 1
python full_mysql_schema_test.py || exit /b 1
python mysql_feature_schema_integrity_test.py || exit /b 1
python mysql_connection_audit_test.py || exit /b 1
cd ..
python scripts\check-page-routing.py || exit /b 1
echo PASS - all offline asset checks complete. Live MySQL and browser testing must be performed separately.
endlocal

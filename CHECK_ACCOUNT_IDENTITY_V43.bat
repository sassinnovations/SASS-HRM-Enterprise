@echo off
setlocal
cd /d "%~dp0"
echo Validating SASS HRM v4.3 administrator account schemas and permissions...
python server\full_mysql_schema_test.py
if errorlevel 1 exit /b 1
python server\account_identity_v43_test.py
if errorlevel 1 exit /b 1
python scripts\check-page-routing.py
if errorlevel 1 exit /b 1
echo Account verification completed. Actual Docker/MySQL tests are separate.

@echo off
setlocal
cd /d "%~dp0"
echo Checking SASS HRM packaged MySQL schema and feature-to-table inventory...
python server\mysql_feature_schema_integrity.py --file-only
if errorlevel 1 exit /b 2
python server\database_feature_coverage.py --check
if errorlevel 1 exit /b 2
python server\mysql_connection_audit_test.py
if errorlevel 1 exit /b 2
python server\mysql_readiness_test.py
if errorlevel 1 exit /b 2
echo PASS: Offline database contract and API-readiness regression tests.
echo To test a real MySQL server run CHECK_ALL_DATABASE_CONNECTIONS.bat.
endlocal

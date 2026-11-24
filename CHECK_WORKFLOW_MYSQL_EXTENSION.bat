@echo off
setlocal
cd /d "%~dp0"
echo === SASS HRM: new 20-table MySQL workflow extension ===
python server\mysql_workflow_extension_test.py
if errorlevel 1 (
 echo ERROR: Workflow migration validation failed. No MySQL changes were made.
 pause
 exit /b 1
)
python server\mysql_feature_schema_integrity.py --file-only
if errorlevel 1 (
 echo ERROR: Full schema package is inconsistent. No MySQL changes were made.
 pause
 exit /b 1
)
if /I "%~1"=="/LIVE" (
 echo === Read-only live MySQL schema check ===
 powershell -NoProfile -ExecutionPolicy Bypass -File scripts\verify-all-mysql-feature-schema.ps1
 if errorlevel 1 (echo ERROR: Live MySQL schema incomplete or unreachable. & pause & exit /b 1)
) else (
 echo NOTE: Run CHECK_WORKFLOW_MYSQL_EXTENSION.bat /LIVE to check your running MySQL database.
)
echo PASS: SASS HRM workflow schema verification completed.
pause

@echo off
setlocal
cd /d "%~dp0server"
python organization_workspace_crud_test.py || exit /b 1
python organization_settings_v26_test.py || exit /b 1
python organization_setup_test.py || exit /b 1
python mysql_connection_audit_test.py || exit /b 1
if errorlevel 1 exit /b 1
echo PASS: Organization CRUD, settings, HRIS import compatibility and MySQL schema audit.
endlocal

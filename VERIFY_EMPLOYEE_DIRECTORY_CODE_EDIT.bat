@echo off
setlocal
cd /d "%~dp0server"
where python >nul 2>&1
if errorlevel 1 (
  echo Python 3 is required to verify Employee HRIS editor.
  exit /b 1
)
python employee_directory_code_edit_test.py
if errorlevel 1 exit /b 1
python official_work_details_edit_test.py
if errorlevel 1 exit /b 1
python route_audit_test.py
if errorlevel 1 exit /b 1
echo Employee directory code edits and previous account profile workflows passed isolated tests.
endlocal

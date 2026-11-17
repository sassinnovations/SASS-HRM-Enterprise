@echo off
setlocal
cd /d "%~dp0server"
echo Testing encrypted vault upload, profile photos, employee CSV import and administrative settings.
echo These tests use a temporary SQLite database and a simulated scanner, not real employee records.
set "SASS_HRM_TESTING=1"
set "DB_ENGINE=sqlite"
set "JWT_SECRET=upload-regression-only-secret-for-local-tests-123456789"
if exist ".venv\Scripts\python.exe" (set "PY=.venv\Scripts\python.exe") else (set "PY=python")
"%PY%" file_upload_settings_test.py
if errorlevel 1 exit /b 1
"%PY%" profile_photo_v44_test.py
if errorlevel 1 exit /b 1
"%PY%" organization_setup_test.py
if errorlevel 1 exit /b 1
"%PY%" admin_settings_v34_test.py
if errorlevel 1 exit /b 1
echo PASS: Upload and settings regression tests passed. Live Docker/MySQL/browser validation is still required.
endlocal

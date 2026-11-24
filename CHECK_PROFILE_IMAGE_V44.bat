@echo off
setlocal
cd /d "%~dp0server"
set "SASS_HRM_TESTING=1"
set "DB_ENGINE=sqlite"
python profile_photo_v44_test.py
if errorlevel 1 exit /b 1
python schema_audit.py --file-only
if errorlevel 1 exit /b 1
echo PASS: Profile photo, optional profile reset and schema source tests.

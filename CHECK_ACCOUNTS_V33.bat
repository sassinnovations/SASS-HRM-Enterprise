@echo off
setlocal
cd /d "%~dp0server"
set SASS_HRM_TESTING=1
set DB_ENGINE=sqlite
set JWT_SECRET=TEST-ONLY-unique-secret-over-40-characters-account-v33
python account_password_v33_test.py
if errorlevel 1 (echo Account security regression failed & exit /b 1)
echo Account security regression passed. No live database data changed.
endlocal

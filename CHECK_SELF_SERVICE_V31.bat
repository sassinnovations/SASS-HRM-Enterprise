@echo off
setlocal
cd /d "%~dp0server"
set "SASS_HRM_TESTING=1"
set "DB_ENGINE=sqlite"
set "JWT_SECRET=temporary-v31-testing-secret-at-least-forty-characters"
python self_service_v31_test.py
if errorlevel 1 ( echo Tests failed. & exit /b 1 )
echo Self-service isolation tests passed.

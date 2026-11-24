@echo off
cd /d "%~dp0"
set "SASS_HRM_TESTING=1"
set "DB_ENGINE=sqlite"
set "JWT_SECRET=LOCAL-CHECK-v46-This-Key-Is-Only-For-Isolated-Testing"
python server\signup_v46_test.py || exit /b 1
python server\full_mysql_schema_test.py || exit /b 1
python scripts\check-page-routing.py || exit /b 1
python scripts\check-single-refresh.py || exit /b 1
echo PASS SASS HRM sign-up v4.6 checks.

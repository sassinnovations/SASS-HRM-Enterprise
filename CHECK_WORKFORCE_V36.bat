@echo off
setlocal
cd /d "%~dp0"
python server\schema_audit.py --file-only || exit /b 1
python server\full_mysql_schema_test.py || exit /b 1
pushd server
set "SASS_HRM_TESTING=1"
set "DB_ENGINE=sqlite"
set "JWT_SECRET=v36-local-check-only-long-1234567890-abcde"
python workforce_planning_v36_test.py
set "RC=%errorlevel%"
popd
exit /b %RC%

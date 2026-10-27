@echo off
setlocal
cd /d "%~dp0"
echo Checking SASS HRM v3.9 performance source and permissions without modifying MySQL...
set "PYTHON=python"
where py >nul 2>&1 && set "PYTHON=py -3"
%PYTHON% server\performance_v39_test.py || exit /b 1
%PYTHON% server\full_mysql_schema_test.py || exit /b 1
%PYTHON% scripts\check-page-routing.py || exit /b 1
%PYTHON% scripts\check-feature-pages.py || exit /b 1
%PYTHON% scripts\check-single-refresh.py || exit /b 1
echo PASS - performance, schema source and navigation checks.
echo Live MySQL and browser testing must still be completed.
exit /b 0

@echo off
setlocal
cd /d "%~dp0"
set PYTHON=python
%PYTHON% server\performance_growth_v40_test.py || exit /b 1
%PYTHON% server\full_mysql_schema_test.py || exit /b 1
%PYTHON% scripts\check-feature-pages.py || exit /b 1
%PYTHON% scripts\check-page-routing.py || exit /b 1
%PYTHON% scripts\check-single-refresh.py || exit /b 1
echo Performance development and feedback source checks passed.

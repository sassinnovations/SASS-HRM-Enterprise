@echo off
setlocal
cd /d "%~dp0"
python server\performance_actions_v41_test.py || exit /b 1
python server\full_mysql_schema_test.py || exit /b 1
python scripts\check-feature-pages.py || exit /b 1
python scripts\check-page-routing.py || exit /b 1
python scripts\check-single-refresh.py || exit /b 1
echo PASS: v4.1 performance actions, MySQL coverage, routing, and Refresh data controls.

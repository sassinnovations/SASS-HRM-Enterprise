@echo off
setlocal
cd /d "%~dp0"
python server\performance_journal_v42_test.py || exit /b 1
python server\full_mysql_schema_test.py || exit /b 1
python scripts\check-feature-pages.py || exit /b 1
python scripts\check-page-routing.py || exit /b 1
python scripts\check-single-refresh.py || exit /b 1
echo PASS: v4.2 role-scoped evidence, goal journal, database schema and 70 separate page URLs.

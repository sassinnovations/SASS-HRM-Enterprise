@echo off
setlocal
cd /d "%~dp0"
python scripts\check-page-routing.py || exit /b 1
python scripts\check-feature-pages.py --csv || exit /b 1
python scripts\check-global-search-v37.py || exit /b 1
python server\global_search_v37_test.py || exit /b 1
python server\full_mysql_schema_test.py || exit /b 1
echo PASS: v3.7 global search checks.

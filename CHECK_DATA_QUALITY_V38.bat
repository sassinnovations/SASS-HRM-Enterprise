@echo off
setlocal
cd /d "%~dp0"
python scripts\check-data-quality-v38.py || exit /b 1
python scripts\check-page-routing.py || exit /b 1
python scripts\check-feature-pages.py --csv || exit /b 1
python server\full_mysql_schema_test.py || exit /b 1
python server\data_quality_v38_test.py || exit /b 1
echo PASS: v3.8 HR data quality center and individual page checks.

@echo off
setlocal
cd /d "%~dp0"
python server\data_quality_import_test.py || exit /b 1
python server\data_quality_v38_test.py || exit /b 1
python server\organization_setup_test.py || exit /b 1
python server\full_mysql_schema_test.py || exit /b 1
python server\mysql_feature_schema_integrity.py --file-only || exit /b 1
echo PASS: HR Data Quality import and settings tests, schema and legacy HRIS workflows.
endlocal

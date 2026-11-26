@echo off
setlocal
cd /d "%~dp0server"
python module_excel_center_test.py || exit /b 1
python feature_screen_integrations_test.py || exit /b 1
python full_mysql_schema_test.py || exit /b 1
echo Excel module center isolated checks completed successfully.

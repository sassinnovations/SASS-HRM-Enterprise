@echo off
setlocal
cd /d "%~dp0server"
python official_work_details_all_roles_test.py || exit /b 1
python official_work_details_edit_test.py || exit /b 1
python profile_v29_test.py || exit /b 1
python full_mysql_schema_test.py || exit /b 1
python mysql_feature_schema_integrity_test.py || exit /b 1
echo PASS: Official Details form, role controls and MySQL schema checks
endlocal

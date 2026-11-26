@echo off
setlocal
cd /d "%~dp0"
echo === Offline source and CRUD verification (does NOT connect to production MySQL) ===
python scripts\audit_feature_links.py --check || exit /b 1
cd server || exit /b 1
python feature_screen_integrations_test.py || exit /b 1
python consolidated_catalog_crud_test.py || exit /b 1
python admin_settings_v34_test.py || exit /b 1
python workforce_planning_v36_test.py || exit /b 1
python culture_suite_test.py || exit /b 1
python employee_directory_code_edit_test.py || exit /b 1
python feature_consolidation_crud_test.py || exit /b 1
echo.
echo PASS: offline feature linkage and catalog CRUD regression.
echo LIVE MYSQL NOT TESTED. To check live MySQL metadata and SELECT access,
echo review CHECK_ALL_DATABASE_CONNECTIONS.bat with your deployment administrator.
endlocal

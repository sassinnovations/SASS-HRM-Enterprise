@echo off
setlocal
cd /d "%~dp0"
echo [1/5] Offline feature index and API route inventory
python scripts\audit_feature_registry.py || exit /b 1
echo [2/5] New CRUD regression
python server\feature_consolidation_crud_test.py || exit /b 1
echo [3/5] Organization preference and office regression
python server\organization_settings_v26_test.py || exit /b 1
python server\organization_workspace_crud_test.py || exit /b 1
echo [4/5] Employee code regression
python server\employee_directory_code_edit_test.py || exit /b 1
echo [5/5] Admin settings regressions
python server\admin_settings_v34_test.py || exit /b 1
python server\compensation_settings_v32_test.py || exit /b 1
echo PASS: feature consolidation offline checks completed
endlocal

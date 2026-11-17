@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"
set "PYTHON=python"
where python >nul 2>&1 || (echo Python 3 is required to run payroll tests.& exit /b 1)
set "PASS=0"
for %%T in (payroll_workbench_controls_test.py payroll_delete_test.py payroll_esi_review_test.py compensation_ops_test.py compensation_settings_v32_test.py full_mysql_schema_test.py mysql_schema_status_test.py) do (
  echo Checking %%T ...
  "%PYTHON%" "server\%%T"
  if errorlevel 1 (echo FAILED %%T & exit /b 1)
  set /a PASS+=1
)
echo SUCCESS: !PASS! offline payroll and database checks passed.
echo NOTE: Live MySQL, frontend build and real payroll compliance must be checked on your deployment.
exit /b 0

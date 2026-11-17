@echo off
setlocal EnableExtensions
set "ROOT=%~dp0"
if not exist "%ROOT%server\hiring_pipeline_test.py" (
 echo FAIL: Extract the complete updated SASS_HRM_Enterprise folder before running this script.
 exit /b 1
)
where python >nul 2>&1
if errorlevel 1 (
 echo Python not found in PATH. Install Python and the server requirements first.
 exit /b 1
)
pushd "%ROOT%server"
echo [1/4] Hiring stage workflows, permissions, reviews, requirements, and audit events
python hiring_pipeline_test.py
if errorlevel 1 goto FAIL
echo [2/4] Full MySQL schema and source coverage
python full_mysql_schema_test.py
if errorlevel 1 goto FAIL
echo [3/4] Existing recruitment API checks
python talent_ops_test.py
if errorlevel 1 goto FAIL
echo [4/4] Configurable stage requirements and permissions
python hiring_stage_settings_test.py
if errorlevel 1 goto FAIL
popd
echo PASS: Hiring pipeline offline tests completed.
echo Note: Live MySQL, frontend production build and browser clicks still require separate checks.
exit /b 0
:FAIL
popd
echo FAIL: See the Python error above.
exit /b 1

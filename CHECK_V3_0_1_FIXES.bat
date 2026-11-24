@echo off
setlocal
cd /d "%~dp0"
where python >nul 2>&1
if errorlevel 1 (
  echo Python is required. Install it or run the script with Python 3.
  exit /b 1
)
echo Checking MySQL approval compatibility and account permissions in an isolated database...
python server\mysql_sql_compat_test.py
if errorlevel 1 exit /b 1
echo Checking local-workspace distribution protections...
python scripts\verify-v24-package.py --workspace
if errorlevel 1 exit /b 1
echo Checking frontend/backend version consistency...
python scripts\verify-v23-connection.py
if errorlevel 1 exit /b 1
echo Checking navigation and layout structure...
python scripts\verify-design-parity.py
if errorlevel 1 exit /b 1
echo SASS HRM v3.0.1 maintenance checks PASSED.
endlocal

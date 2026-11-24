@echo off
setlocal
cd /d "%~dp0"
echo Checking SASS HRM v3.0 workspace modules...
python server\workspace_v30_test.py
if errorlevel 1 (
  echo Workspace security test failed. Check Python requirements.
  exit /b 1
)
python scripts\verify-design-parity.py
if errorlevel 1 exit /b 1
python scripts\verify-v24-package.py --workspace
if errorlevel 1 exit /b 1
echo SASS HRM workspace checks passed.
endlocal

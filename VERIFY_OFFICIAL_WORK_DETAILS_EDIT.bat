@echo off
setlocal
cd /d "%~dp0server"
where python >nul 2>&1
if errorlevel 1 (
  echo Python 3 is required to run the official HR details regression test.
  exit /b 1
)
python official_work_details_edit_test.py
if errorlevel 1 (
  echo Official work details editing verification FAILED.
  exit /b 1
)
python profile_v29_test.py
if errorlevel 1 exit /b 1
python accounts_v25_test.py
if errorlevel 1 exit /b 1
echo Official work details edit, profile and account tests passed.
endlocal

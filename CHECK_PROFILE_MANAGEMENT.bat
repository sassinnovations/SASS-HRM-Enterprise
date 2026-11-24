@echo off
setlocal
cd /d "%~dp0server"
set "SASS_HRM_TESTING=1"
set "DB_ENGINE=sqlite"
set "JWT_SECRET=PROFILE-ONLY-ISOLATED-TEST-SECRET-GREATER-THAN-40-CHARACTERS"
python profile_v29_test.py
if errorlevel 1 (
  echo Profile management tests FAILED.
  exit /b 1
)
echo Profile management tests passed.
endlocal

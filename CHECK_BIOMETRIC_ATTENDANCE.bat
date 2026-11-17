@echo off
setlocal
cd /d "%~dp0server"
python biometric_attendance_test.py
if errorlevel 1 (
  echo Attendance tests failed.
  exit /b 1
)
echo Offline attendance modality tests passed. Live scanners still require testing.
pause

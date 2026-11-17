@echo off
setlocal
cd /d "%~dp0"
set "PYTHON=python"
if exist "server\.venv\Scripts\python.exe" set "PYTHON=server\.venv\Scripts\python.exe"
"%PYTHON%" "server\payroll_delete_test.py"
if errorlevel 1 (
  echo Payroll deletion tests FAILED. Review the output before deploying.
  pause
  exit /b 1
)
"%PYTHON%" "server\payroll_esi_review_test.py"
if errorlevel 1 (
  echo Payroll ESI regression tests FAILED.
  pause
  exit /b 1
)
"%PYTHON%" "server\compensation_ops_test.py"
if errorlevel 1 (
  echo Compensation operation tests FAILED.
  pause
  exit /b 1
)
echo Payroll deletion, ESI and compensation regression tests PASSED.
pause
endlocal

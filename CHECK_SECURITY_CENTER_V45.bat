@echo off
setlocal
cd /d "%~dp0"
set "PYTHON=python"
if exist ".venv\Scripts\python.exe" set "PYTHON=.venv\Scripts\python.exe"
if exist "server\.venv\Scripts\python.exe" set "PYTHON=server\.venv\Scripts\python.exe"
echo SASS HRM v4.5 - account security feature checks (isolated, no live DB modifications)
"%PYTHON%" server\security_center_v45_test.py || exit /b 1
"%PYTHON%" server\full_mysql_schema_test.py || exit /b 1
"%PYTHON%" scripts\check-page-routing.py || exit /b 1
"%PYTHON%" scripts\check-single-refresh.py || exit /b 1
"%PYTHON%" scripts\verify-v24-package.py || exit /b 1
echo All v4.5 security feature source checks passed.
exit /b 0

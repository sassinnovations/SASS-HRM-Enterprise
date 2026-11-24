@echo off
setlocal
cd /d "%~dp0"
where python >nul 2>&1
if errorlevel 1 (
    echo Python is required to run this read-only frontend check.
    exit /b 1
)
python scripts\check-single-refresh.py
if errorlevel 1 exit /b 1
python scripts\check-page-routing.py
if errorlevel 1 exit /b 1
python scripts\verify-design-parity.py
if errorlevel 1 exit /b 1
python scripts\verify-v21-ui.py
if errorlevel 1 exit /b 1
echo All static refresh and navigation checks passed.
endlocal

@echo off
setlocal
cd /d "%~dp0"
where python >nul 2>&1
if errorlevel 1 (
  echo Python 3 is required to validate the page routes.
  exit /b 1
)
python scripts\check-page-routing.py
if errorlevel 1 exit /b 1
python scripts\verify-v23-connection.py
if errorlevel 1 exit /b 1
python scripts\verify-v24-package.py --workspace
if errorlevel 1 exit /b 1
echo Page routing static checks passed. For live browser tests, start Docker then run CHECK_BROWSER_V2.bat.
endlocal

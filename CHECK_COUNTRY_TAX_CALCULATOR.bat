@echo off
setlocal
cd /d "%~dp0server"
set "SASS_HRM_TESTING=1"
python country_tax_calculator_test.py
if errorlevel 1 (
 echo Country tax calculator tests FAILED.
 exit /b 1
)
echo Country tax calculator tests PASSED.

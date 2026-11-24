@echo off
setlocal
cd /d "%~dp0"
echo Validating SASS HRM Compensation Settings v3.5.0...
python scripts\check-page-routing.py || exit /b 1
python scripts\verify-design-parity.py || exit /b 1
set "SASS_HRM_TESTING=1"
set "DB_ENGINE=sqlite"
set "JWT_SECRET=compensation-check-bat-test-only-not-for-production-2026"
cd server
python compensation_settings_v32_test.py || exit /b 1
python compensation_ops_test.py || exit /b 1
echo PASS: compensation settings and workflows regression checks completed.
endlocal

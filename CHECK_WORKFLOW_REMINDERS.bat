@echo off
setlocal
cd /d "%~dp0"
echo Validating SASS HRM v3.5 workflow reminders...
python scripts\check-page-routing.py || exit /b 1
python scripts\verify-v24-package.py --workspace || exit /b 1
set SASS_HRM_TESTING=1
set DB_ENGINE=sqlite
set JWT_SECRET=test-suite-only-secret-string-at-least-40-characters-abcdefg
cd server
python workflow_reminders_v35_test.py || exit /b 1
echo Workflow Reminders checks passed. This does not test live Docker/MySQL.
endlocal

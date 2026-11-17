@echo off
setlocal
cd /d "%~dp0"
echo ================================================================
echo SASS HRM candidate search release - full source and offline regression audit
echo ================================================================
echo No existing MySQL database is modified by these checks.
python server\schema_audit.py --file-only || goto FAILED
python scripts\check-page-routing.py || goto FAILED
python scripts\check-single-refresh.py || goto FAILED
python scripts\verify-login-design.py || goto FAILED
python scripts\check-cross-module-reliability.py || goto FAILED
python scripts\verify-design-parity.py || goto FAILED
python scripts\verify-v24-package.py --workspace || goto FAILED
python server\full_mysql_schema_test.py || goto FAILED
python scripts\check-empty-candidate-bundle.py || goto FAILED
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\test-backend.ps1" || goto FAILED
echo.
echo PASS: Source and isolated tests completed.
echo IMPORTANT: Live MySQL, Docker, and browser testing are separate.
echo Use CHECK_FULL_MYSQL_SCHEMA.bat for a READ-ONLY live DB check.
echo Run npm ci and npm run build inside web to verify the production bundle.
exit /b 0
:FAILED
echo.
echo FAILED: See the first error above. Do not reset your MySQL database.
exit /b 1

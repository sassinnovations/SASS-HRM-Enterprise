@echo off
setlocal
cd /d "%~dp0"
echo Verifying isolated AI copilot / source database contracts...
python server\ai_copilot_test.py || goto failed
python server\full_mysql_schema_test.py || goto failed
python server\mysql_feature_schema_integrity_test.py || goto failed
python server\feature_screen_integrations_test.py || goto failed
echo.
echo AI Copilot isolated checks passed. LIVE MySQL and complete web build not verified.
exit /b 0
:failed
echo.
echo Verification failed; inspect the command output.
exit /b 1

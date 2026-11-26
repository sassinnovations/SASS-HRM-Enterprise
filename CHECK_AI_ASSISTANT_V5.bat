@echo off
setlocal
cd /d "%~dp0"
python server\ai_copilot_v5_test.py || goto failed
python server\ai_assistant_v4_test.py || goto failed
python server\ai_copilot_test.py || goto failed
python scripts\check-ai-right-dock.py || goto failed
python server\http_500_health_test.py || goto failed
echo.
echo SASS AI v5 isolated checks passed. Live provider, MySQL and frontend build are NOT verified.
exit /b 0
:failed
echo SASS AI verification failed. Review the test output.
exit /b 1

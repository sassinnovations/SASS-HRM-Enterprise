@echo off
setlocal
cd /d "%~dp0"
python server\ai_assistant_v4_test.py
if errorlevel 1 exit /b 1
python server\ai_copilot_test.py
if errorlevel 1 exit /b 1
python scripts\check-ai-right-dock.py
if errorlevel 1 exit /b 1
echo All selected SASS AI Assistant v4 checks passed.

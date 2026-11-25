@echo off
setlocal
cd /d "%~dp0"
set PYTHONPATH=server
python server\ai_copilot_v7_test.py
if errorlevel 1 exit /b 1
python server\ai_copilot_v6_test.py
if errorlevel 1 exit /b 1
python server\ai_copilot_v5_test.py
if errorlevel 1 exit /b 1
echo PASS: SASS AI Bot v7 and prior regressions
endlocal

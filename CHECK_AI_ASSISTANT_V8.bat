@echo off
setlocal
cd /d "%~dp0"
echo Running SASS AI Bot v8 isolated feature-command and workflow tests...
python server\ai_copilot_v8_test.py
if errorlevel 1 (
  echo AI v8 tests failed.
  exit /b 1
)
echo AI v8 tests passed.
endlocal

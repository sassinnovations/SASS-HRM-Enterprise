@echo off
setlocal
cd /d "%~dp0server"
python ai_copilot_v6_test.py
if errorlevel 1 (
  echo AI v6 tests failed.
  exit /b 1
)
echo AI v6 isolated tests passed.
endlocal

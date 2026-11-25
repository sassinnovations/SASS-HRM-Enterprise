@echo off
setlocal
cd /d "%~dp0"
echo Testing SASS AI Bot v9 (isolated SQLite; no production writes)...
python server\ai_copilot_v9_test.py
if errorlevel 1 (
  echo AI v9 tests failed.
  exit /b 1
)
echo AI v9 tests passed.
endlocal

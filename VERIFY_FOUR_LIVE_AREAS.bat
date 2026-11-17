@echo off
setlocal
cd /d "%~dp0"
echo SASS HRM live four-area verification (read-only by default)
echo Start the full Docker application before running this check.
echo.
set "VAULT_OPTION="
set /p "ANSWER=Test a real temporary secure-vault file upload and removal? [y/N]: "
if /I "%ANSWER%"=="Y" set "VAULT_OPTION=-TestVaultUpload"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\verify-four-live-areas.ps1" %VAULT_OPTION%
if errorlevel 1 (
  echo.
  echo FAIL: Some checks did not pass. Copy the printed errors into ChatGPT.
  pause
  exit /b 1
)
echo.
echo All executed checks passed. Browser click-through testing still required.
pause

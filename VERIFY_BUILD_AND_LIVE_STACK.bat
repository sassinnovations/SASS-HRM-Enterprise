@echo off
setlocal EnableExtensions
cd /d "%~dp0"
echo ========================================================
echo SASS HRM - Frontend Build and Live MySQL Verification
 echo Read-only until the optional temporary file upload choice.
echo Database volumes WILL NOT be reset.
echo ========================================================
echo.
echo [1/3] Building the actual production frontend...
call "%~dp0VERIFY_FRONTEND_BUILD.bat"
if errorlevel 1 goto BUILD_FAILED
 echo.
echo [2/3] Checking Docker containers, actual MySQL tables and ClamAV...
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\verify-docker-full.ps1"
if errorlevel 1 goto DOCKER_FAILED
 echo.
echo [3/3] Checking live API routes, optional sign-in and file vault...
call "%~dp0VERIFY_FOUR_LIVE_AREAS.bat"
if errorlevel 1 goto LIVE_FAILED
 echo.
echo PASS: Completed build and live-stack checks.
echo NEXT: Optional browser UI verification:
echo       python scripts\verify-browser-readonly.py
exit /b 0
:BUILD_FAILED
echo FAIL: The frontend build did not complete. Inspect FRONTEND_BUILD_VERIFICATION_LOG.txt.
exit /b 1
:DOCKER_FAILED
echo FAIL: Live Docker / actual MySQL schema check did not pass.
echo Do NOT run docker compose down -v and do NOT delete database volumes.
exit /b 1
:LIVE_FAILED
echo FAIL: One or more live API checks failed. Review the console messages.
exit /b 1

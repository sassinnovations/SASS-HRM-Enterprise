@echo off
setlocal EnableExtensions
set "ROOT=%~dp0"
set "WEB=%ROOT%web"
set "LOG=%ROOT%FRONTEND_BUILD_VERIFICATION_LOG.txt"

> "%LOG%" echo SASS HRM Enterprise Frontend Build Verification
>> "%LOG%" echo ===============================================
>> "%LOG%" echo Date: %DATE% %TIME%
echo.
echo SASS HRM - Frontend Production Build Check
echo Log: "%LOG%"
echo.

if not exist "%WEB%\package.json" (
  echo FAIL: web\package.json not found. Run this BAT from the extracted SASS_HRM_Enterprise root.
  >> "%LOG%" echo FAIL: Missing web\package.json
  exit /b 1
)
where node >nul 2>&1
if errorlevel 1 (
  echo FAIL: Node.js missing. Install the current Node.js LTS version.
  >> "%LOG%" echo FAIL: Node.js not installed
  exit /b 1
)
where npm >nul 2>&1
if errorlevel 1 (
  echo FAIL: npm missing. Repair the Node.js installation.
  >> "%LOG%" echo FAIL: npm not installed
  exit /b 1
)

echo Node version:
node --version
node --version >> "%LOG%" 2>&1
echo npm version:
call npm --version
call npm --version >> "%LOG%" 2>&1

pushd "%WEB%"
echo.
echo [1/3] Installing locked frontend dependencies ...
>> "%LOG%" echo.
>> "%LOG%" echo [1/3] npm ci --no-audit --no-fund
call npm ci --no-audit --no-fund >> "%LOG%" 2>&1
if errorlevel 1 goto INSTALL_FAIL

echo [2/3] Compiling TypeScript and building Vite ...
>> "%LOG%" echo.
>> "%LOG%" echo [2/3] npm run build
call npm run build >> "%LOG%" 2>&1
if errorlevel 1 goto BUILD_FAIL

echo [3/3] Checking generated assets ...
if not exist "dist\index.html" goto OUTPUT_FAIL
if not exist "dist\assets\*.js" goto OUTPUT_FAIL
>> "%LOG%" echo PASS: web\dist\index.html and JavaScript bundle present
popd
echo.
echo PASS: The production frontend build completed.
echo This does NOT prove browser interaction, login, backend, payroll, or MySQL functionality.
echo To preview locally, run these commands in the web folder:
echo    npm run preview -- --host 127.0.0.1
echo Then open the URL shown in the terminal and test key workflows with your own backend.
echo Full log: "%LOG%"
exit /b 0

:INSTALL_FAIL
popd
echo FAIL: npm ci failed. Check npm registry/DNS/proxy connectivity and the log.
echo Full log: "%LOG%"
exit /b 1

:BUILD_FAIL
popd
echo FAIL: TypeScript or Vite build failed. Review errors at end of log.
echo Full log: "%LOG%"
exit /b 1

:OUTPUT_FAIL
popd
echo FAIL: Build exited without expected dist assets. Review log.
echo Full log: "%LOG%"
exit /b 1

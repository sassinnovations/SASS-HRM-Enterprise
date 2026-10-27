@echo off
setlocal
cd /d "%~dp0web"
where npm >nul 2>&1 || (echo ERROR: Node.js and npm are required. & exit /b 1)
echo Cleaning platform-specific frontend dependencies; source code is not changed.
if exist node_modules rmdir /s /q node_modules
call npm ci --no-audit --no-fund
if errorlevel 1 (echo ERROR: Dependency install failed. & exit /b 1)
call npm run build
if errorlevel 1 (echo ERROR: Frontend build failed. & exit /b 1)
echo Frontend dependencies and production build verified.
endlocal

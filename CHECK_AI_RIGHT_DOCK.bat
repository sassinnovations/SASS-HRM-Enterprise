@echo off
setlocal
cd /d "%~dp0"
python scripts\check-ai-right-dock.py
if errorlevel 1 exit /b 1
echo.
echo Right-side AI bot layout source checks passed.
echo Run npm ci and npm run build from web on a machine with npm connectivity.
exit /b 0

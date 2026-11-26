@echo off
setlocal
cd /d "%~dp0"
python scripts\check-ai-right-dock.py
if errorlevel 1 exit /b 1
echo Floating AI icon and window source checks passed.
echo For a complete browser build run npm ci and npm run build from the web folder.
exit /b 0

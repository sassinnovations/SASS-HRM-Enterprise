@echo off
cd /d "%~dp0"
python scripts\check-cross-module-reliability.py
if errorlevel 1 exit /b 1
python scripts\check-page-routing.py
if errorlevel 1 exit /b 1
python scripts\check-single-refresh.py
if errorlevel 1 exit /b 1
echo Reliability source checks passed.

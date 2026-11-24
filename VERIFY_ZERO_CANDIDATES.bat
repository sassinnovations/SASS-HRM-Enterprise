@echo off
setlocal
cd /d "%~dp0server"
if not exist ".env" (
 echo Missing server\.env. Configure MySQL first.
 exit /b 1
)
python verify_zero_candidates.py
if errorlevel 1 (
 echo WARNING: The live MySQL candidate library is NOT confirmed empty.
 exit /b 1
)
echo Verified: candidate database has zero records and zero imports.
exit /b 0

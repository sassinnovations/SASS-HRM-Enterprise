@echo off
setlocal
cd /d "%~dp0server"
if not exist ".env" (
  echo ERROR: Configure server\.env first, using SETUP_SASS_HRM.bat.
  pause
  exit /b 1
)
set "WORKBOOK=%~1"
if "%WORKBOOK%"=="" (
  echo ERROR: No workbook selected. Provide the path to your NEW .xlsx file.
  echo Example: IMPORT_CANDIDATES_TO_MYSQL.bat "C:\HRM\my_new_candidates.xlsx"
  echo No candidate records were imported.
  pause
  exit /b 1
)
python import_candidates.py "%WORKBOOK%"
if errorlevel 1 (
  echo.
  echo Candidate import FAILED. Check MySQL service and server\.env.
  pause
  exit /b 1
)
echo.
echo Candidate import completed. Open Talent Management ^> Candidate Search ^& Database.
pause

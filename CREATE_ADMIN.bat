@echo off
cd /d "%~dp0"
echo Initial SASS HRM account: Administrator + Developer diagnostics
set /p HR_EMAIL=Administrator work email: 
if not defined HR_EMAIL (
  echo Administrator work email is required.
  pause
  exit /b 1
)
set /p HR_NAME=Administrator full display name: 
set /p HR_CODE=Employee code [SASS-ADM-001]: 
if not defined HR_CODE set "HR_CODE=SASS-ADM-001"
set /p HR_LOCATION=Office location: 
cd server
if not exist .venv\Scripts\python.exe (
  py -3 -m venv .venv
)
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe create_admin.py --email "%HR_EMAIL%" --name "%HR_NAME%" --code "%HR_CODE%" --location "%HR_LOCATION%" --developer
pause

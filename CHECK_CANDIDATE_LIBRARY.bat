@echo off
setlocal
cd /d "%~dp0"
python scripts\check-empty-candidate-bundle.py
if errorlevel 1 (
 echo Candidate zero-preload verification FAILED.
 exit /b 1
)
cd /d "%~dp0server"
python candidate_library_test.py
if errorlevel 1 (
 echo Candidate library tests FAILED.
 pause
 exit /b 1
)
cd /d "%~dp0"
echo Candidate search, secure Excel removal, archive restore, editing, sorting, role permissions and zero-preload checks PASSED.
pause

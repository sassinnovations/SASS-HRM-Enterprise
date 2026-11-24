@echo off
setlocal
cd /d "%~dp0"
where python >nul 2>&1
if errorlevel 1 (
  echo Python is required for automated talent checks.
  exit /b 1
)
echo Checking package consistency...
python scripts\verify-talent-v281.py --workspace || exit /b 1
echo Running isolated talent regression tests (no live database required)...
pushd server
python talent_ops_test.py
if errorlevel 1 (popd & exit /b 1)
python talent_v281_test.py
if errorlevel 1 (popd & exit /b 1)
popd
echo Talent checks passed. You may now verify the running Docker app.
exit /b 0

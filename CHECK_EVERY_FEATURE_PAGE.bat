@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>nul
if not errorlevel 1 (
    set "RUNPY=py -3"
) else (
    set "RUNPY=python"
)
echo Checking all SASS HRM page links, screen mounts, access rules and browser fallback...
%RUNPY% scripts\check-feature-pages.py --csv
if errorlevel 1 goto fail
echo.
echo Checking direct URL refresh, navigation, Back/Forward and single Refresh data...
%RUNPY% scripts\check-page-routing.py
if errorlevel 1 goto fail
%RUNPY% scripts\check-single-refresh.py
if errorlevel 1 goto fail
echo.
echo PASS: Source coverage for all 60 feature pages.
echo See docs\SASS_HRM_66_PAGE_CHECKLIST.csv for individual page URLs.
echo Live Docker, browser and database workflows still require manual testing.
pause
exit /b 0
:fail
echo.
echo ERROR: One or more feature-page checks failed.
pause
exit /b 1

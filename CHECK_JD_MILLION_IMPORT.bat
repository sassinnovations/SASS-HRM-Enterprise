@echo off
setlocal
cd /d "%~dp0server"
set SASS_HRM_TESTING=1
set DB_ENGINE=sqlite
set JWT_SECRET=jd-million-tests-only-secret-more-than-forty-characters
python job_descriptions_test.py || exit /b 1
python job_descriptions_million_test.py || exit /b 1
python mysql_feature_schema_integrity_test.py || exit /b 1
echo.
echo PASS: JD import capacity and schema checks completed. Live MySQL not tested.
endlocal

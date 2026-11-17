@echo off
setlocal
cd /d "%~dp0"
where docker >nul 2>&1
if errorlevel 1 (
 echo ERROR: Docker Desktop is required for a live MySQL check.
 exit /b 2
)
docker info >nul 2>&1
if errorlevel 1 (
 echo ERROR: Docker Desktop is not running.
 exit /b 2
)
echo Ensuring MySQL service is running. Existing named volumes are preserved.
docker compose -f docker-compose.full.yml up -d mysql
if errorlevel 1 exit /b 2
echo Building the current backend verifier image.
docker compose -f docker-compose.full.yml build api
if errorlevel 1 exit /b 2
echo Running a read-only audit. No MySQL volumes or data will be reset.
docker compose -f docker-compose.full.yml run --rm --no-deps api python check_all_mysql_connections.py --probe-tables
if errorlevel 1 (
 echo Database verification failed. Review messages above; do not reset MySQL volumes.
 exit /b 2
)
echo All database table-access probes passed; test the screens and workflows separately.
endlocal

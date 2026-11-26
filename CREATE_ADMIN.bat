@echo off
setlocal EnableExtensions DisableDelayedExpansion
pushd "%~dp0" || exit /b 1

if not exist "docker-compose.full.yml" goto :wrong_folder
if not exist ".env" goto :missing_config
if not exist "server\.env" goto :missing_config

where docker >nul 2>&1
if errorlevel 1 goto :docker_missing
docker info --format "{{.ServerVersion}}" >nul 2>&1
if errorlevel 1 goto :docker_stopped
docker compose version >nul 2>&1
if errorlevel 1 goto :compose_missing

echo Checking the running SASS HRM API and its configured MySQL database...
docker compose -f "docker-compose.full.yml" exec -T api python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/ready',timeout=10).close()"
if errorlevel 1 goto :not_ready

echo.
echo This creates only the first HR administrator. No existing account will be reset.
echo Enter a NEW password locally when the hidden prompt appears.
echo.
docker compose -f "docker-compose.full.yml" exec api python -c "import os,sys; from mysql_backend import raw_mysql_connection; from create_admin import main; sys.stdin.isatty() and sys.stderr.isatty() or sys.exit('Open this launcher in an interactive Windows terminal.'); os.environ.get('DB_ENGINE','').strip().lower()=='mysql' or sys.exit('The running API is not configured for MySQL.'); db=raw_mysql_connection(); cur=db.cursor(); cur.execute('SELECT DATABASE() AS db_name, EXISTS(SELECT 1 FROM employees LIMIT 1) AS has_employees'); info=cur.fetchone(); not info['has_employees'] or sys.exit('This database already has employee records. Use the existing account or recovery process. Nothing changed.'); cur.execute('SELECT GET_LOCK(CONCAT(LEFT(SHA2(DATABASE(),256),40),\'-sass-admin-bootstrap\'),0) AS acquired'); cur.fetchone()['acquired']==1 or sys.exit('Another first-admin setup is running. Nothing changed.'); print('Target database:',info['db_name']); email=input('Administrator work email: ').strip(); name=input('Administrator full display name: ').strip(); code=input('Employee code [SASS-ADM-001]: ').strip() or 'SASS-ADM-001'; location=input('Office location: ').strip(); email and name and location or sys.exit('Work email, display name and office location are required. Nothing changed.'); sys.argv=['create_admin.py','--email='+email,'--name='+name,'--code='+code,'--location='+location]; main()"
set "rc=%errorlevel%"
if not "%rc%"=="0" goto :bootstrap_failed
echo.
echo Sign in to SASS HRM with the email and new password you entered.
goto :done

:wrong_folder
echo ERROR: Put CREATE_ADMIN.bat in the existing SASS HRM project folder, beside docker-compose.full.yml.
goto :failed

:missing_config
echo ERROR: This folder is missing .env or server\.env. Use the configured project folder. Do not overwrite existing configuration.
goto :failed

:docker_missing
echo ERROR: Docker Desktop command not found.
goto :failed

:docker_stopped
echo ERROR: Docker Desktop is not running or the Docker engine is unavailable.
goto :failed

:compose_missing
echo ERROR: Docker Compose is unavailable. Check the Docker Desktop installation.
goto :failed

:not_ready
echo ERROR: The full Docker stack is not ready. Check the running api and mysql services before trying again.
echo Readiness check: http://localhost:8000/api/ready
goto :failed

:bootstrap_failed
echo.
echo First-admin setup did not complete. Check the message above. Do not reset MySQL.
goto :done

:failed
set "rc=1"

:done
echo.
pause
popd
exit /b %rc%

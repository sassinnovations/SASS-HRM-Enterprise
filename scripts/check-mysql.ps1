$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) { throw 'Docker CLI missing' }
$container = docker compose -f docker-compose.mysql.yml ps -q mysql
if (-not $container) { throw 'MySQL container is not running. Use START_MYSQL.bat' }
$health = docker inspect --format '{{.State.Health.Status}}' $container
if ($health -ne 'healthy') { throw "MySQL unhealthy: $health" }
Write-Host 'PASS: MySQL Docker healthcheck' -ForegroundColor Green
$server = Join-Path $root 'server'
Set-Location $server
$python = if (Test-Path '.venv\Scripts\python.exe') { '.\.venv\Scripts\python.exe' } else { 'python' }
& $python -c "from dotenv import load_dotenv; load_dotenv('.env'); from mysql_backend import raw_mysql_connection,install_schema; c=raw_mysql_connection(); install_schema(c); p=c.cursor(); p.execute('SELECT COUNT(*) AS n FROM information_schema.tables WHERE table_schema=DATABASE()'); print('PASS: schema tables =',p.fetchone()['n']); p.execute('SELECT COUNT(*) AS n FROM employees'); print('PASS: employees =',p.fetchone()['n']); p.close(); c.close()"
if ($LASTEXITCODE -ne 0) { throw 'Backend database connection/query failed; check server/.env and installed Python dependencies' }
# v1.5: check all eight culture and service tables after additive schema installation.
& $python -c "from dotenv import load_dotenv; load_dotenv('.env'); from mysql_backend import raw_mysql_connection; c=raw_mysql_connection(); cur=c.cursor(); needed=('career_plans','career_milestones','employee_voice_cases','employee_voice_messages','discipline_cases','discipline_case_responses','service_categories','service_requests'); cur.execute('SELECT TABLE_NAME AS table_name FROM information_schema.tables WHERE table_schema=DATABASE()'); found={x['table_name'] for x in cur.fetchall()}; missing=set(needed)-found; print('1.5 module tables present:',len(set(needed)&found),'of',len(needed)); cur.close(); c.close(); assert not missing, f'Missing 1.5 module tables: {sorted(missing)}'"
if ($LASTEXITCODE -ne 0) { throw 'The new culture/request desk MySQL tables are missing. Check schema installation logs.' }

Write-Host 'For an API login test, use your administrator account in the browser.' -ForegroundColor Cyan
try {
  $healthApi=Invoke-RestMethod -Method Get -Uri 'http://127.0.0.1:8000/api/health' -TimeoutSec 5
  Write-Host 'PASS: Backend API health' -ForegroundColor Green
} catch { Write-Host 'INFO: Backend API is not running yet. Start START_HERE.bat.' -ForegroundColor Yellow }

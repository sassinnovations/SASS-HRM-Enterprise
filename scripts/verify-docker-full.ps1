$ErrorActionPreference='Stop'
$root=Split-Path -Parent $PSScriptRoot
Set-Location $root
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) { throw 'Docker is unavailable' }
$need=@('mysql','api','web')
foreach ($service in $need) {
  $id=docker compose -f docker-compose.full.yml ps -q $service
  if (-not $id) { throw "$service container does not exist" }
  $state=docker inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}missing{{end}}' $id
  if ($state -ne 'healthy') { throw "$service container is $state, expected healthy" }
  Write-Host "PASS: $service container healthy" -ForegroundColor Green
}
try {
  $api=Invoke-RestMethod -Uri 'http://127.0.0.1:8000/api/health' -TimeoutSec 15
  $proxy=Invoke-RestMethod -Uri 'http://127.0.0.1:5173/api/health' -TimeoutSec 15
  $home=Invoke-WebRequest -Uri 'http://127.0.0.1:5173/' -UseBasicParsing -TimeoutSec 15
} catch { throw "Docker service HTTP smoke test failed: $($_.Exception.Message)" }
if ($api.status -ne 'ok' -or $api.database -ne 'mysql' -or $api.version -ne '4.5.0') { throw 'API must be MySQL-backed and running release v4.5.0; check for a stale process on 8000.' }
if ($proxy.status -ne 'ok' -or $proxy.database -ne 'mysql' -or $proxy.version -ne '4.5.0') { throw 'nginx /api proxy is not reaching the current MySQL-backed FastAPI release.' }
if ($home.StatusCode -ne 200 -or $home.Content -notmatch '<html') { throw 'Frontend HTML was not served by nginx.' }
Write-Host 'PASS: API, nginx reverse proxy, React entry HTML and MySQL engine.' -ForegroundColor Green
# Database schema check executes inside API network/container, avoiding the Windows Python environment.
docker compose -f docker-compose.full.yml exec -T api python deployment_probe.py
if ($LASTEXITCODE -ne 0) { throw 'MySQL table verification failed.' }
Write-Host 'Note: This is infrastructure/read-only smoke verification, not all authenticated business workflows.' -ForegroundColor Yellow

$ErrorActionPreference='Stop'
$root=Split-Path -Parent $PSScriptRoot
Set-Location $root
$expectedVersion=(Get-Content (Join-Path $root 'web/package.json') -Raw | ConvertFrom-Json).version
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) { throw 'Docker is unavailable' }
# MySQL, API and web explicitly require health checks. The ClamAV image may
# have no Docker HEALTHCHECK, so its actual clamd protocol must be probed below.
foreach ($service in @('mysql','api','web')) {
  $id=docker compose -f docker-compose.full.yml ps -q $service
  if (-not $id) { throw "$service container does not exist" }
  $state=docker inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}missing{{end}}' $id
  if ($LASTEXITCODE -ne 0 -or $state -ne 'healthy') { throw "$service container is $state, expected healthy" }
  Write-Host "PASS: $service container healthy" -ForegroundColor Green
}
$scannerId=docker compose -f docker-compose.full.yml ps -q vault-av
if (-not $scannerId) { throw 'ClamAV container does not exist' }
$scannerRunning=docker inspect --format '{{.State.Running}}' $scannerId
if ($LASTEXITCODE -ne 0 -or $scannerRunning -ne 'true') { throw 'ClamAV container is not running' }
# Verify the real antivirus service is ready, not just that its container started.
# Run from the API container where the private docker DNS name vault-av resolves.
$ping = @'
import socket
with socket.create_connection(('vault-av',3310),timeout=8) as s:
    s.settimeout(8)
    s.sendall(b'zPING\0')
    reply=s.recv(32)
    if reply.rstrip(b'\0\r\n')!=b'PONG':
        raise RuntimeError(f'ClamAV returned {reply!r}, expected PONG')
print('PASS: ClamAV scanner accepts protocol PING')
'@
$ping | docker compose -f docker-compose.full.yml exec -T api python -
if ($LASTEXITCODE -ne 0) { throw 'ClamAV scanner not ready. Check signature downloads, scanner logs, and vault-av service.' }
try {
  $api=Invoke-RestMethod -Uri 'http://127.0.0.1:8000/api/health' -TimeoutSec 15
  $proxy=Invoke-RestMethod -Uri 'http://127.0.0.1:5173/api/health' -TimeoutSec 15
  $homeResponse=Invoke-WebRequest -Uri 'http://127.0.0.1:5173/' -UseBasicParsing -TimeoutSec 15
} catch { throw "Docker service HTTP smoke test failed: $($_.Exception.Message)" }
if ($api.status -ne 'ok' -or $api.database -ne 'mysql' -or $api.version -ne $expectedVersion) { throw 'API must be MySQL-backed and running the packaged release version; check for a stale process on 8000.' }
if ($proxy.status -ne 'ok' -or $proxy.database -ne 'mysql' -or $proxy.version -ne $expectedVersion) { throw 'nginx /api proxy is not reaching the current MySQL-backed FastAPI release.' }
if ($homeResponse.StatusCode -ne 200 -or $homeResponse.Content -notmatch '<html') { throw 'Frontend HTML was not served by nginx.' }
Write-Host 'PASS: API, nginx reverse proxy, React entry HTML, MySQL, and ClamAV scanner.' -ForegroundColor Green
# Database schema check executes inside API network/container, avoiding the Windows Python environment.
docker compose -f docker-compose.full.yml exec -T api python deployment_probe.py
if ($LASTEXITCODE -ne 0) { throw 'MySQL table verification failed.' }
Write-Host 'Note: This is infrastructure/read-only smoke verification, not all authenticated business workflows.' -ForegroundColor Yellow

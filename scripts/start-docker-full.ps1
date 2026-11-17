$ErrorActionPreference='Stop'
$root=Split-Path -Parent $PSScriptRoot
Set-Location $root
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) { throw 'Docker Desktop is not installed or docker is not on PATH.' }
if (-not (Get-Command python -ErrorAction SilentlyContinue)) { throw 'Python is needed for the configuration preflight; install Python or run it using py -3.' }
python (Join-Path $PSScriptRoot 'check-runtime-config.py')
if ($LASTEXITCODE -ne 0) { throw 'Configuration failed. Do not start containers with inconsistent MySQL credentials.' }
docker info *> $null
if ($LASTEXITCODE -ne 0) { throw 'Docker Desktop engine is not running. Start Docker Desktop.' }
docker compose -f docker-compose.full.yml config --quiet
if ($LASTEXITCODE -ne 0) { throw 'Full-stack Compose configuration failed.' }
Write-Host 'Building the frontend and backend and starting the MySQL stack...' -ForegroundColor Cyan
Write-Host 'First build requires internet access to PyPI and npm. Existing database volume will be retained.' -ForegroundColor Yellow
docker compose -f docker-compose.full.yml up --build --detach
if ($LASTEXITCODE -ne 0) {
  Write-Host 'Inspect errors using: docker compose -f docker-compose.full.yml logs --tail 100' -ForegroundColor Yellow
  throw 'Docker build or startup failed. No database volumes were deleted.'
}
Write-Host 'Waiting for MySQL, FastAPI, nginx and the live ClamAV scanner...' -ForegroundColor Cyan
$ready=$false
# ClamAV does not necessarily expose a Docker health status. The readiness
# test must check that its daemon responds to PING, not require a health label.
for ($attempt=0; $attempt -lt 90; $attempt++) {
  $healthy=$true
  foreach ($service in @('mysql','api','web')) {
    $id=docker compose -f docker-compose.full.yml ps -q $service 2>$null
    if (-not $id) { $healthy=$false; break }
    $state=docker inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}missing{{end}}' $id 2>$null
    if ($state -ne 'healthy') { $healthy=$false; break }
  }
  if ($healthy) {
    $avId=docker compose -f docker-compose.full.yml ps -q vault-av 2>$null
    if (-not $avId) { $healthy=$false }
    else {
      $avRunning=docker inspect --format '{{.State.Running}}' $avId 2>$null
      if ($avRunning -ne 'true') { $healthy=$false }
    }
  }
  if ($healthy) {
    # Scanner signature initialization can take several minutes on first start.
    # Silence expected connection errors while the scanner is initializing.
    $probe = @'
import socket
with socket.create_connection(('vault-av',3310),timeout=3) as s:
    s.settimeout(3)
    s.sendall(b'zPING\0')
    assert s.recv(32).rstrip(b'\0\r\n') == b'PONG'
'@
    $probe | docker compose -f docker-compose.full.yml exec -T api python - *> $null
    if ($LASTEXITCODE -eq 0) { $ready=$true; break }
  }
  Start-Sleep -Seconds 3
}
if (-not $ready) {
  docker compose -f docker-compose.full.yml ps
  Write-Host 'Use: docker compose -f docker-compose.full.yml logs --tail 100 api mysql web' -ForegroundColor Yellow
  throw 'Some Docker services failed health checks. See logs (do not paste passwords).'
}
& (Join-Path $PSScriptRoot 'verify-docker-full.ps1')
if ($LASTEXITCODE -ne 0) { throw 'The stack started but service verification failed.' }
Write-Host 'SASS HRM ready: http://localhost:5173' -ForegroundColor Green
Write-Host 'MySQL Workbench: 127.0.0.1:3307; API: http://localhost:8000/api/health' -ForegroundColor Cyan

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
  throw 'Docker Desktop not found. Install and start Docker Desktop, or configure MySQL 8.4 manually.'
}
docker info | Out-Null
if ($LASTEXITCODE -ne 0) { throw 'Docker Desktop engine is not running. Start Docker Desktop and retry.' }
docker compose -f docker-compose.mysql.yml up -d mysql
if ($LASTEXITCODE -ne 0) { throw 'MySQL container failed to start. Try: docker compose -f docker-compose.mysql.yml logs mysql' }
Write-Host 'MySQL container started. Waiting for the healthcheck...' -ForegroundColor Cyan
for ($attempt=1; $attempt -le 45; $attempt++) {
  $container = docker compose -f docker-compose.mysql.yml ps -q mysql
  if (-not $container) { throw 'No MySQL container was returned by Docker Compose' }
  $health = docker inspect --format '{{.State.Health.Status}}' $container 2>$null
  if ($health -eq 'healthy') {
    Write-Host 'MySQL 8.4 is healthy. Server: 127.0.0.1 port 3307; database: sass_hrm' -ForegroundColor Green
    exit 0
  }
  Start-Sleep -Seconds 2
}
throw 'MySQL did not become healthy. Check Docker Desktop / container logs.'

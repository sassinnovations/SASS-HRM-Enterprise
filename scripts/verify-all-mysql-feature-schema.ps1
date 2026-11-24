$ErrorActionPreference = 'Stop'
$project = Split-Path -Parent $PSScriptRoot
Set-Location $project
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) { throw 'Docker Desktop is required for live MySQL checks.' }
docker info *> $null
if ($LASTEXITCODE -ne 0) { throw 'Docker Desktop is not running.' }
Write-Host 'Starting MySQL service only; existing named volumes are preserved.' -ForegroundColor Cyan
docker compose -f docker-compose.full.yml up -d mysql
if ($LASTEXITCODE -ne 0) { throw 'Unable to start the MySQL service.' }
Write-Host 'Building verifier backend container (no database writes)...' -ForegroundColor Cyan
docker compose -f docker-compose.full.yml build api
if ($LASTEXITCODE -ne 0) { throw 'Unable to prepare verifier image.' }
Write-Host 'Read-only metadata check: tables, columns, indexes and FK references.' -ForegroundColor Cyan
docker compose -f docker-compose.full.yml run --rm --no-deps api python mysql_feature_schema_integrity.py --live
if ($LASTEXITCODE -ne 0) { throw 'Schema integrity check failed; see above. Do not reset MySQL volumes.' }
Write-Host 'PASS: all MySQL schema objects required by the current SASS HRM release are present.' -ForegroundColor Green

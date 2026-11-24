param([switch]$Install)
$ErrorActionPreference = 'Stop'
$project = Split-Path -Parent $PSScriptRoot
Set-Location $project

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) { throw 'Docker Desktop is required for live MySQL validation.' }
docker info *> $null
if ($LASTEXITCODE -ne 0) { throw 'Start Docker Desktop and wait for the Docker engine to become healthy.' }

Write-Host 'Checking full SASS HRM schema in source...' -ForegroundColor Cyan
# Avoid importing the API / JWT secret while checking the static schema.
$py = if (Get-Command python -ErrorAction SilentlyContinue) { 'python' } else { throw 'Python 3 is needed for local schema validation.' }
& $py (Join-Path $project 'server/schema_audit.py') --file-only
if ($LASTEXITCODE -ne 0) { throw 'Schema source is incomplete. Live changes cancelled.' }

Write-Host 'Starting MySQL only (preserving existing Docker volumes)...' -ForegroundColor Cyan
docker compose -f docker-compose.full.yml up -d mysql
if ($LASTEXITCODE -ne 0) { throw 'Could not start MySQL. Check .env and Docker Desktop.' }

Write-Host 'Preparing isolated backend verifier image...' -ForegroundColor Cyan
docker compose -f docker-compose.full.yml build api
if ($LASTEXITCODE -ne 0) { throw 'Backend image build failed.' }

if ($Install) {
  Write-Host 'INSTALL: new tables/indexes only. Existing data will not be deleted.' -ForegroundColor Yellow
  Write-Host 'Make and verify a backup BEFORE this step, especially with real HR/payroll data.' -ForegroundColor Yellow
  Write-Host 'Preflight will refuse duplicate work emails and unexpected existing-column mismatches.' -ForegroundColor Yellow
  $answer = Read-Host 'After verifying your backup, type APPLY to continue (anything else cancels)'
  if ($answer -cne 'APPLY') { throw 'No schema changes were made (cancelled).' }
  docker compose -f docker-compose.full.yml run --rm --no-deps api python schema_audit.py --install --live --confirm APPLY --expected-database sass_hrm
} else {
  docker compose -f docker-compose.full.yml run --rm --no-deps api python schema_audit.py --live
}
if ($LASTEXITCODE -ne 0) { throw 'Schema verification found missing tables/columns, or MySQL connection failed. No database volumes were reset.' }
Write-Host 'PASS: MySQL has all SASS HRM application tables and expected columns.' -ForegroundColor Green

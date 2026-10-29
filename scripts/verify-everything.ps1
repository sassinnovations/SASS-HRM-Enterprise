# SASS HRM: backend regressions + real frontend production build
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
python (Join-Path $PSScriptRoot 'check-page-routing.py')
if ($LASTEXITCODE -ne 0) { throw 'Distinct module route validation failed.' }
python (Join-Path $PSScriptRoot 'verify-design-parity.py')
if ($LASTEXITCODE -ne 0) { throw 'Design parity validation failed.' }
python (Join-Path $PSScriptRoot 'test-design-parity.py')
if ($LASTEXITCODE -ne 0) { throw 'Design validator regression tests failed.' }
python (Join-Path $PSScriptRoot 'verify-v23-connection.py')
if ($LASTEXITCODE -ne 0) { throw 'v2.4 database identity validation failed.' }
python (Join-Path $PSScriptRoot 'verify-v24-package.py') --workspace
if ($LASTEXITCODE -ne 0) { throw 'Release package hygiene checks failed.' }
python (Join-Path $PSScriptRoot 'verify-v21-ui.py')
if ($LASTEXITCODE -ne 0) { throw 'v2.1 shared UI checks failed.' }
python (Join-Path $root 'server/schema_audit.py') --file-only
if ($LASTEXITCODE -ne 0) { throw 'MySQL schema declarations do not cover all backend features.' }
python (Join-Path $root 'server/full_mysql_schema_test.py')
if ($LASTEXITCODE -ne 0) { throw 'Full MySQL schema regression failed.' }
& (Join-Path $PSScriptRoot 'test-backend.ps1')
if ($LASTEXITCODE -ne 0) { throw 'Backend test suite failed.' }
Set-Location (Join-Path $root 'web')
if (-not (Test-Path 'node_modules')) {
  Write-Host 'Installing frontend dependencies (requires internet)...' -ForegroundColor Cyan
  npm ci --no-audit --no-fund
  if ($LASTEXITCODE -ne 0) { throw 'npm dependency installation failed.' }
}
Write-Host 'Building frontend (TypeScript + Vite)...' -ForegroundColor Cyan
npm run build
if ($LASTEXITCODE -ne 0) { throw 'Frontend production build failed.' }
Write-Host 'Backend tests and frontend production build completed successfully.' -ForegroundColor Green

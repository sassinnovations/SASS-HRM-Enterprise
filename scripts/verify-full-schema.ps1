param([switch]$Install)
$ErrorActionPreference = 'Stop'
$project = Split-Path -Parent $PSScriptRoot
$server = Join-Path $project 'server'
Set-Location $server
$python = if (Test-Path '.venv\Scripts\python.exe') { '.\.venv\Scripts\python.exe' } else { 'python' }

Write-Host 'Checking full SASS HRM schema in source...' -ForegroundColor Cyan
& $python schema_audit.py --file-only
if ($LASTEXITCODE -ne 0) { throw 'Schema source is incomplete. Live changes cancelled.' }

if ($Install) {
  Write-Host 'INSTALL: new tables/indexes only. Existing data will not be deleted.' -ForegroundColor Yellow
  Write-Host 'Make and verify a backup BEFORE this step, especially with real HR/payroll data.' -ForegroundColor Yellow
  $answer = Read-Host 'After verifying your backup, type APPLY to continue (anything else cancels)'
  if ($answer -cne 'APPLY') { throw 'No schema changes were made (cancelled).' }
  & $python -c "from dotenv import load_dotenv; load_dotenv('.env'); import schema_audit; raise SystemExit(schema_audit.main(['--live','--install','--confirm','APPLY']))"
} else {
  & $python -c "from dotenv import load_dotenv; load_dotenv('.env'); import schema_audit; raise SystemExit(schema_audit.main(['--live']))"
}
if ($LASTEXITCODE -ne 0) { throw 'Schema verification found missing tables/columns, or MySQL connection failed.' }
Write-Host 'PASS: MySQL has all SASS HRM application tables and expected columns.' -ForegroundColor Green

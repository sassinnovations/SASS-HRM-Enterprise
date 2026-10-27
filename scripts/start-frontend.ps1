# Start the SASS HRM React portal and show frontend failures in this window.
$ErrorActionPreference = 'Stop'
$web = Join-Path (Split-Path -Parent $PSScriptRoot) 'web'
Set-Location $web
if (-not (Get-Command node -ErrorAction SilentlyContinue)) { throw 'Node.js is missing. Install a current Node.js LTS release.' }
if (-not (Get-Command npm -ErrorAction SilentlyContinue)) { throw 'npm is missing. Reinstall Node.js with npm.' }
if (-not (Test-Path 'node_modules')) {
  Write-Host 'Installing frontend dependencies for first run...' -ForegroundColor Yellow
  npm ci --no-audit --no-fund
  if ($LASTEXITCODE -ne 0) { throw 'npm install failed. Check the npm error above.' }
}
Write-Host 'SASS HRM portal: http://localhost:5173 (stop old Vite sessions first)' -ForegroundColor Cyan
Write-Host 'If the browser shows a blank page, run REPAIR_FRONTEND.bat from the project root.' -ForegroundColor Yellow
npm run dev -- --force
if ($LASTEXITCODE -ne 0) { throw 'Vite failed. Check the first error shown above.' }

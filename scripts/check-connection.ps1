# Check SASS HRM v0.9.1 localhost services without changing any HR data.
$ErrorActionPreference = 'Continue'
Write-Host 'SASS HRM - Local Connection Check' -ForegroundColor Cyan
Write-Host '================================='
function Check-Json([string]$Url, [string]$Label) {
  try {
    $result = Invoke-RestMethod -Uri $Url -TimeoutSec 5 -Method Get
    Write-Host "PASS: $Label -> $Url" -ForegroundColor Green
    return $true
  } catch {
    Write-Host "FAIL: $Label -> $Url" -ForegroundColor Red
    Write-Host "  $($_.Exception.Message)" -ForegroundColor DarkYellow
    return $false
  }
}
$backend = Check-Json 'http://127.0.0.1:8000/api/health' 'FastAPI backend health'
if (-not $backend) {
  Write-Host ''
  Write-Host 'Fix: Open a NEW PowerShell window at the project root and run:' -ForegroundColor Yellow
  Write-Host '  powershell -ExecutionPolicy Bypass -File .\scripts\start-backend.ps1'
  Write-Host 'Keep that PowerShell window open; resolve any red errors there.'
}
$frontend = Check-Json 'http://127.0.0.1:5173/' 'Vite frontend'
if (-not $frontend) {
  Write-Host 'Fix: Open another PowerShell window and run:' -ForegroundColor Yellow
  Write-Host '  powershell -ExecutionPolicy Bypass -File .\scripts\start-frontend.ps1'
}
Write-Host ''
Write-Host 'If both are PASS, go to http://localhost:5173 and hard-reload (Ctrl+Shift+R).'
Write-Host 'If it still fails, send the FIRST red message from the backend or frontend terminal.'
if (-not $backend -or -not $frontend) { exit 1 }

$ErrorActionPreference='Continue'
$root=Split-Path -Parent $PSScriptRoot
Write-Host 'SASS HRM v2.3 connection diagnostic (read-only)' -ForegroundColor Cyan
foreach ($port in @(5173,8000,3306)) {
  $listeners=@(Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue)
  if (-not $listeners.Count) { Write-Host "Port ${port}: no listener" -ForegroundColor Yellow; continue }
  foreach ($listener in $listeners) {
    $process=Get-Process -Id $listener.OwningProcess -ErrorAction SilentlyContinue
    $processName=if($process){$process.ProcessName}else{'Unknown'}
    Write-Host "Port ${port}: $processName (PID $($listener.OwningProcess))"
  }
}
foreach ($url in @('http://127.0.0.1:8000/api/health','http://127.0.0.1:5173/api/health')) {
  try {
    $result=Invoke-RestMethod -Uri $url -TimeoutSec 5
    Write-Host "$url => status=$($result.status), database=$($result.database), version=$($result.version)"
    if ($result.status -ne 'ok' -or $result.database -ne 'mysql' -or $result.version -ne '4.5.0') {
      Write-Host 'WARNING: This address is not serving the required MySQL v4.5.0 backend.' -ForegroundColor Red
    }
  } catch { Write-Host "$url => unavailable: $($_.Exception.Message)" -ForegroundColor Yellow }
}
Write-Host 'If a stale process owns 5173 or 8000, close its original terminal first.' -ForegroundColor Cyan

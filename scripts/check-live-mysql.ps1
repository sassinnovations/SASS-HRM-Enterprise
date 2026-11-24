# Require an actual MySQL-backed SASS HRM API. Isolated SQLite test runs are not acceptable.
$ErrorActionPreference = 'Stop'
try {
  $health = Invoke-RestMethod -Uri 'http://127.0.0.1:8000/api/health' -Method Get -TimeoutSec 15
} catch {
  throw "Cannot reach SASS HRM API at http://127.0.0.1:8000/api/health. Start START_MYSQL.bat and then the backend. Details: $($_.Exception.Message)"
}
if ($health.status -ne 'ok') { throw "API reported unhealthy: $($health.status)" }
if ($health.database -ne 'mysql') {
  throw "This backend is using '$($health.database)', not MySQL. Stop the old test server and start the current SASS HRM backend with DB_ENGINE=mysql."
}
Write-Host 'PASS: SASS HRM API health reports DB_ENGINE=mysql. A live query still needs verification via VERIFY_DOCKER_FULL.bat.' -ForegroundColor Green
Write-Host 'IMPORTANT: This checks configured engine only. Run VERIFY_DOCKER_FULL.bat to query the real MySQL schema and verify live table access.' -ForegroundColor Yellow

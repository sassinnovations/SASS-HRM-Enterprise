# Require an actual MySQL-backed SASS HRM API. Isolated SQLite test runs are not acceptable.
$ErrorActionPreference = 'Stop'
try {
  $health = Invoke-RestMethod -Uri 'http://127.0.0.1:8000/api/health' -Method Get -TimeoutSec 15
} catch {
  throw "Cannot reach SASS HRM API at http://127.0.0.1:8000/api/health. Start START_MYSQL.bat and then the backend. Details: $($_.Exception.Message)"
}
if ($health.status -ne 'ok') { throw "API reported unhealthy: $($health.status)" }
if ($health.database -ne 'mysql') {
  throw "This backend is using '$($health.database)', not MySQL. Stop the old test server and start the real v1.6 backend with DB_ENGINE=mysql."
}
Write-Host 'PASS: Running SASS HRM backend responds healthy and is backed by MySQL.' -ForegroundColor Green
Write-Host 'IMPORTANT: This verifies API engine selection, not payroll, security compliance or full database migrations.' -ForegroundColor Yellow

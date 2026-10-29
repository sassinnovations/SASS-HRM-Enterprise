$ErrorActionPreference='Stop'
$root=Split-Path -Parent $PSScriptRoot
Set-Location $root
if ((Test-Path '.env') -or (Test-Path 'server/.env')) {
  throw 'Existing configuration detected. No files changed. Back up your existing installation before modifying passwords.'
}
function New-Secret([int]$n) {
  $bytes=[byte[]]::new($n)
  $rng=[System.Security.Cryptography.RandomNumberGenerator]::Create()
  try { $rng.GetBytes($bytes) } finally { $rng.Dispose() }
  return [BitConverter]::ToString($bytes).Replace('-','').ToLowerInvariant()
}
$mysqlPass=New-Secret 28
$jwt=New-Secret 48

function Write-EnvFile([string]$Path, [string]$Content) {
  $normalized = $Content.Replace("`r`n", "`n").Replace("`r", "`n")
  [System.IO.File]::WriteAllText($Path, $normalized, [System.Text.UTF8Encoding]::new($false))
}

Write-EnvFile -Path '.env' @"
MYSQL_DATABASE=sass_hrm
MYSQL_USER=sass_hrm_app
MYSQL_PASSWORD=$mysqlPass
"@

Write-EnvFile -Path 'server/.env' @"
APP_ENV=development
DB_ENGINE=mysql
MYSQL_HOST=127.0.0.1
MYSQL_PORT=3306
MYSQL_DATABASE=sass_hrm
MYSQL_USER=sass_hrm_app
MYSQL_PASSWORD=$mysqlPass
JWT_SECRET=$jwt
CORS_ORIGINS=http://localhost:5173
PUBLIC_APP_URL=http://localhost:5173
SMTP_HOST=
SMTP_PORT=587
SMTP_USER=
SMTP_PASSWORD=
SMTP_FROM=
"@

Write-Host 'Created random MySQL and JWT credentials. NO employees or fake company records were created.' -ForegroundColor Green
Write-Host 'Next: point server/.env at MySQL, then CREATE_ADMIN.bat, then START_HERE.bat.' -ForegroundColor Cyan
Write-Host 'Before inviting employees, configure SMTP_HOST, SMTP_USER, SMTP_PASSWORD and SMTP_FROM in server/.env.' -ForegroundColor Yellow

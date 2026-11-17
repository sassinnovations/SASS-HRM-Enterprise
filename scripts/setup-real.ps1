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
$rootPass=New-Secret 28
$jwt=New-Secret 48
$vaultBytes=[byte[]]::new(32)
$rng=[System.Security.Cryptography.RandomNumberGenerator]::Create()
try { $rng.GetBytes($vaultBytes) } finally { $rng.Dispose() }
$vaultKey=[Convert]::ToBase64String($vaultBytes).TrimEnd('=').Replace('+','-').Replace('/','_')
# Fernet keys must be base64-encoded 32-byte values including padding.
$vaultKey += '=' * ((4 - $vaultKey.Length % 4) % 4)
@"
MYSQL_DATABASE=sass_hrm
MYSQL_USER=sass_hrm_app
MYSQL_PASSWORD=$mysqlPass
MYSQL_ROOT_PASSWORD=$rootPass
"@ | Set-Content -Encoding ascii '.env'
@"
APP_ENV=development
DB_ENGINE=mysql
MYSQL_HOST=127.0.0.1
MYSQL_PORT=3307
MYSQL_DATABASE=sass_hrm
MYSQL_USER=sass_hrm_app
MYSQL_PASSWORD=$mysqlPass
JWT_SECRET=$jwt
VAULT_FERNET_KEY=$vaultKey
VAULT_AV_HOST=127.0.0.1
VAULT_AV_PORT=3310
CORS_ORIGINS=http://localhost:5173
PUBLIC_APP_URL=http://localhost:5173
SMTP_HOST=
SMTP_PORT=587
SMTP_USER=
SMTP_PASSWORD=
SMTP_FROM=
"@ | Set-Content -Encoding ascii 'server/.env'
Write-Host 'Created random MySQL, JWT, and secure vault encryption credentials. NO employees or fake records were created.' -ForegroundColor Green
Write-Host 'Next: START_MYSQL.bat, then CREATE_ADMIN.bat, then START_HERE.bat.' -ForegroundColor Cyan
Write-Host 'Before inviting employees, configure SMTP_HOST, SMTP_USER, SMTP_PASSWORD and SMTP_FROM in server/.env.' -ForegroundColor Yellow

Write-Host 'The vault also needs the local ClamAV scanner container (started alongside MySQL). Preserve server/.env and the key in your secure backups.' -ForegroundColor Yellow

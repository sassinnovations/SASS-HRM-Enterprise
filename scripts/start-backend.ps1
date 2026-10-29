# SASS HRM Enterprise - local server (Windows PowerShell)
$ErrorActionPreference = 'Stop'
$server = Join-Path (Split-Path -Parent $PSScriptRoot) 'server'
Set-Location $server
if (-not (Test-Path '.venv\Scripts\python.exe')) {
  if (Get-Command py -ErrorAction SilentlyContinue) { py -3 -m venv .venv }
  elseif (Get-Command python -ErrorAction SilentlyContinue) { python -m venv .venv }
  else { throw 'Python is missing. Install Python 3.10+ and select Add Python to PATH.' }
  if ($LASTEXITCODE -ne 0) { throw 'Could not create the Python environment. Check the Python error above.' }
}
$python = Join-Path $server '.venv\Scripts\python.exe'
& $python -m pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) { throw 'Backend dependency installation failed. Check the pip error above.' }
if (-not (Test-Path '.env')) { throw 'Missing server/.env. Run SETUP_SASS_HRM.bat before starting the system.' }
Write-Host 'MySQL backend selected from server/.env. The API does not start a database.' -ForegroundColor Cyan
Write-Host 'API health check: http://localhost:8000/api/health' -ForegroundColor Cyan
Write-Host 'API documentation: http://localhost:8000/docs' -ForegroundColor Cyan
Write-Host 'Keep this window OPEN while signing in.' -ForegroundColor Yellow
& $python -m uvicorn main:app --reload --host 127.0.0.1 --port 8000
if ($LASTEXITCODE -ne 0) { throw 'FastAPI could not start. Check for port 8000 conflicts or the first Python exception above.' }

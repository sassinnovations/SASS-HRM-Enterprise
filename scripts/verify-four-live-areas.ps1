# Read-only by default. Optional vault upload test creates and removes ONE marked test file.
# Works with Windows PowerShell 5.1+ against the local SASS HRM installation.
param(
    [switch]$SkipLogin,
    [switch]$TestVaultUpload
)
$ErrorActionPreference='Stop'
$base='http://127.0.0.1:5173'
$api='http://127.0.0.1:8000'
# Derive the expected API version from the frontend package; do not hardcode stale releases.
$releaseRoot=Split-Path -Parent $PSScriptRoot
$script:expectedVersion=(Get-Content (Join-Path $releaseRoot 'web/package.json') -Raw | ConvertFrom-Json).version
$script:failures=New-Object 'System.Collections.Generic.List[string]'
$script:passed=0
function Check([string]$name,[scriptblock]$body) {
    try {
        & $body
        Write-Host "PASS: $name" -ForegroundColor Green
        $script:passed++
    } catch {
        $detail=$_.Exception.Message
        Write-Host "FAIL: $name - $detail" -ForegroundColor Red
        $script:failures.Add("$name : $detail")
    }
}
function Require([bool]$condition,[string]$message) {
    if (-not $condition) { throw $message }
}
function GetJson([string]$url) {
    Invoke-RestMethod -Uri $url -Headers $script:headers -TimeoutSec 20
}
$script:headers=@{}
$script:health=$null
Check 'API health reports a MySQL engine (schema query verified separately)' {
    $script:health=GetJson "$api/api/health"
    Require ($script:health.status -eq 'ok') 'API did not report healthy'
    Require ($script:health.database -eq 'mysql') 'API is not using MySQL'
    Require ($script:health.version -eq $script:expectedVersion) 'Wrong backend version; rebuild/restart the current project'
}
Check 'MySQL-backed API through the browser reverse proxy' {
    $proxy=GetJson "$base/api/health"
    Require ($proxy.status -eq 'ok' -and $proxy.database -eq 'mysql') 'Reverse proxy is not reaching the live MySQL API'
    Require ($proxy.version -eq $script:expectedVersion) 'Reverse proxy reaches a stale backend'
}
Check 'Frontend HTML, main JS and direct navigation links (HTTP smoke test)' {
    foreach ($route in @('/','/workspace/overview','/talent/candidate-search-database','/compensation/payroll-workbench','/services/secure-document-vault','/settings/my-workspace')) {
        $response=Invoke-WebRequest -Uri "$base$route" -UseBasicParsing -TimeoutSec 20
        Require ($response.StatusCode -eq 200 -and $response.Content -match '<html') "Frontend page route failed: $route"
    }
    $index=(Invoke-WebRequest -Uri "$base/" -UseBasicParsing -TimeoutSec 20).Content
    $match=[regex]::Match($index,'<script[^>]+src=["''](?<path>/[^"'']+)["'']')
    Require ($match.Success) 'Frontend HTML does not reference a JavaScript entry file'
    $asset=Invoke-WebRequest -Uri ($base+$match.Groups['path'].Value) -UseBasicParsing -TimeoutSec 30
    Require ($asset.StatusCode -eq 200 -and $asset.RawContentLength -gt 100) 'Frontend JavaScript could not be loaded'
}

if (-not $SkipLogin -and $script:health -and $script:health.database -eq 'mysql' -and $script:health.version -eq $script:expectedVersion) {
    Write-Host ''
    Write-Host 'Optional authenticated read-only checks: enter your HRM email, or press Enter to skip.'
    $email=Read-Host 'HRM sign-in email'
    if ($email) {
        $passwordSecure=Read-Host 'HRM password (hidden, not stored)' -AsSecureString
        $ptr=[Runtime.InteropServices.Marshal]::SecureStringToBSTR($passwordSecure)
        try {
            $password=[Runtime.InteropServices.Marshal]::PtrToStringBSTR($ptr)
            $payload=@{ email=$email; password=$password } | ConvertTo-Json -Compress
            $login=Invoke-RestMethod -Uri "$api/api/auth/login" -Method Post -ContentType 'application/json' -Body $payload -TimeoutSec 25
            Require ([bool]$login.token -and [bool]$login.user) 'Sign-in response missing token/user'
            $script:headers=@{Authorization="Bearer $($login.token)"}
            $script:user=$login.user
            Write-Host 'PASS: Authenticated login succeeded.' -ForegroundColor Green
            $script:passed++
        } catch {
            $script:failures.Add("Login : $($_.Exception.Message)")
            Write-Host "FAIL: Login - $($_.Exception.Message)" -ForegroundColor Red
        } finally {
            if ($ptr -ne [IntPtr]::Zero) { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($ptr) }
            Remove-Variable password,payload,login -ErrorAction SilentlyContinue
        }
    }
}

if ($script:headers.ContainsKey('Authorization')) {
    Check 'Employee identity and self-service profile' {
        $me=GetJson "$api/api/auth/me"
        $profile=GetJson "$api/api/profile/me"
        Require ($me.id -eq $script:user.id) 'Identity mismatch'
        Require ($null -ne $profile) 'Profile response was missing'
    }
    Check 'Payroll rules, payslips, compensation settings, and read-only readiness' {
        $rules=GetJson "$api/api/payroll-v2/rules"
        $statements=GetJson "$api/api/payroll-v2/my-statements"
        $compensation=GetJson "$api/api/compensation/settings"
        if ($script:user.role -eq 'admin') {
            $period=(Get-Date -Format 'yyyy-MM')
            if ($period -ge '2026-04' -and $period -le '2027-03') {
                $preflight=GetJson "$api/api/payroll-v2/preflight?month=$period"
                Require ($preflight.month -eq $period -and $null -ne $preflight.issues) 'Payroll preflight did not return expected fields'
            }
        }
        Require ([bool]$rules.supported_tax_calculators) 'Payroll rules missing'
        Require ($null -ne $compensation.settings) 'Compensation settings missing'
    }
    Check 'Secure vault encryption and actual ClamAV readiness' {
        $vault=GetJson "$api/api/vault/status"
        Require ($vault.enabled -eq $true) 'Vault is disabled (check VAULT_FERNET_KEY and live ClamAV scanner)'
        $files=GetJson "$api/api/vault/files"
    }
    Check 'Candidate job roles and database search endpoint' {
        if ($script:user.role -in @('admin','manager')) {
            $options=GetJson "$api/api/candidate-library/options"
            $candidatePage=GetJson "$api/api/candidate-library?page=1&page_size=1"
            Require ($null -ne $options) 'Candidate filters missing'
            Require ($null -ne $candidatePage) 'Candidate search unavailable'
        } else {
            Write-Host 'SKIP: Candidate search is restricted to managers and HR admins.' -ForegroundColor Yellow
        }
    }
    if ($script:user.role -eq 'admin') {
        Check 'Administrator settings and employee/payroll data read' {
            $settings=GetJson "$api/api/admin/settings/overview"
            $people=GetJson "$api/api/employees"
            $runs=GetJson "$api/api/payroll-v2/runs"
            Require ($null -ne $settings) 'Admin settings unavailable'
            Require ($null -ne $people) 'Employee API unavailable'
            Require ($null -ne $runs) 'Payroll workbench unavailable'
        }
    }
    if ($TestVaultUpload) {
        Check 'Real encrypted file upload, download and delete (writes only a temporary test file)' {
            $vault=GetJson "$api/api/vault/status"
            Require ($vault.enabled -eq $true) 'File vault is disabled'
            $message="SASS HRM local verification $([guid]::NewGuid().ToString('N'))"
            $data=[System.Text.Encoding]::UTF8.GetBytes($message)
            $body=@{
                employee_id=[int]$script:user.id
                filename='sass-hrm-verification.txt'
                mime_type='text/plain'
                category='Other'
                data_base64=[Convert]::ToBase64String($data)
            } | ConvertTo-Json -Compress
            $id=$null
            try {
                $uploaded=Invoke-RestMethod -Uri "$api/api/vault/files" -Headers $script:headers -Method Post -ContentType 'application/json' -Body $body -TimeoutSec 35
                $id=$uploaded.id
                Require ($id -gt 0) 'Upload did not return a file ID'
                $tmp=[IO.Path]::GetTempFileName()
                try {
                    Invoke-WebRequest -Uri "$api/api/vault/files/$id/download" -Headers $script:headers -OutFile $tmp -UseBasicParsing -TimeoutSec 35
                    $downloaded=[IO.File]::ReadAllBytes($tmp)
                    Require (([Convert]::ToBase64String($downloaded)) -eq ([Convert]::ToBase64String($data))) 'Downloaded file differs from uploaded data'
                } finally { Remove-Item $tmp -Force -ErrorAction SilentlyContinue }
            } finally {
                if ($id) {
                    try {
                        $deleted=Invoke-RestMethod -Uri "$api/api/vault/files/$id" -Headers $script:headers -Method Delete -TimeoutSec 20
                        Require ($deleted.deleted -eq $true) 'Temporary test file was not deleted'
                    } catch {
                        Write-Warning "Temporary test file ID $id may remain and should be deleted through SASS HRM. $($_.Exception.Message)"
                        throw
                    }
                }
            }
        }
    }
} else {
    Write-Host 'NOTE: Authenticated vault, payroll, settings and employee workflow checks were not run.' -ForegroundColor Yellow
}
Write-Host ''
Write-Host "Completed: $script:passed checks passed; $($script:failures.Count) failed." -ForegroundColor Cyan
Write-Host 'IMPORTANT: HTTP checks do not prove every frontend button works; full browser click testing and payroll approval are still required.' -ForegroundColor Yellow
Write-Host 'IMPORTANT: Payroll uses reference calculations; this check does not make payments, create pay runs, or validate tax compliance.' -ForegroundColor Yellow
if ($script:failures.Count -gt 0) { exit 1 }
exit 0

$ErrorActionPreference = 'Stop'
$server=Join-Path (Split-Path -Parent $PSScriptRoot) 'server'
Set-Location $server
$env:SASS_HRM_TESTING='1'
$env:DB_ENGINE='sqlite'
$env:JWT_SECRET='test-suite-only-secret-string-at-least-40-characters-abcdefg'
$python=if(Test-Path '.venv\Scripts\python.exe'){'.\.venv\Scripts\python.exe'}else{'python'}
& $python runtime_diagnostics_test.py
if($LASTEXITCODE -ne 0){throw 'Runtime identity regression checks failed'}
& $python real_baseline_test.py
if($LASTEXITCODE -ne 0){throw 'Clean-install tests failed'}
& $python admin_developer_test.py
if($LASTEXITCODE -ne 0){throw 'Admin and developer access tests failed'}
& $python merged_release_test.py
if($LASTEXITCODE -ne 0){throw 'Merged feature tests failed'}
& $python route_audit_test.py
if($LASTEXITCODE -ne 0){throw 'Static API endpoint role audit failed'}
& $python culture_suite_test.py
if($LASTEXITCODE -ne 0){throw 'Career, Employee Voice, Discipline and Request Desk tests failed'}
& $python organization_setup_test.py
if($LASTEXITCODE -ne 0){throw 'Company setup and employee import tests failed'}
& $python talent_ops_test.py
if($LASTEXITCODE -ne 0){throw 'Talent Management workflow and privacy tests failed'}
& $python compensation_ops_test.py
if($LASTEXITCODE -ne 0){throw 'Compensation Operations and permission tests failed'}
& $python compensation_settings_v32_test.py
if($LASTEXITCODE -ne 0){throw 'v3.2 compensation settings persistence and role tests failed'}
& $python culture_ops_test.py
if($LASTEXITCODE -ne 0){throw 'Culture Operations v1.9 and confidential timeline tests failed'}
& $python employee_services_v20_test.py
if($LASTEXITCODE -ne 0){throw 'Employee Services v2.0 workflow and privacy tests failed'}
& $python exports_v24_test.py
if($LASTEXITCODE -ne 0){throw 'New attendance and audit export access tests failed'}
& $python accounts_v25_test.py
if($LASTEXITCODE -ne 0){throw 'Account administration, password reset and JWT security tests failed'}
& $python account_password_v33_test.py
if($LASTEXITCODE -ne 0){throw 'v3.3 password, sub-admin restrictions, JWT revocation test failed'}
& $python admin_settings_v34_test.py
if($LASTEXITCODE -ne 0){throw 'v3.4 settings permissions, validation and persistence test failed'}
Write-Host 'Clean-install, Developer, Talent, Culture, Compensation and Employee Services v2.0 tests passed' -ForegroundColor Green

& $python calendar_v27_test.py
if($LASTEXITCODE -ne 0){throw 'v2.7 private calendar authorization and event workflow tests failed'}
Write-Host 'Private calendar v2.7 permission checks passed' -ForegroundColor Green

& $python profile_v29_test.py
if($LASTEXITCODE -ne 0){throw 'Profile v2.9 management checks failed'}
Write-Host 'Profile management v2.9 checks passed' -ForegroundColor Green

# The full project check also covers v2.6/2.8/3.0 modules, which were missing
# from the original aggregate launcher even though they shipped in the ZIP.
foreach ($test in @('organization_settings_v26_test.py','talent_v281_test.py','workspace_v30_test.py','mysql_sql_compat_test.py','self_service_v31_test.py')) {
  & $python $test
  if ($LASTEXITCODE -ne 0) { throw "Backend regression failed: $test" }
}
Write-Host 'All versioned backend suites, including v3 workspace and MySQL SQL compatibility, passed.' -ForegroundColor Green

& $python workflow_reminders_v35_test.py
if($LASTEXITCODE -ne 0){throw "v3.5 workflow reminder privacy and deduplication tests failed"}
Write-Host "v3.5 workflow reminders regression passed" -ForegroundColor Green

& $python workforce_planning_v36_test.py
if($LASTEXITCODE -ne 0){throw "v3.6 leave coverage and task template security regression failed"}
Write-Host "v3.6 workforce planning checks passed" -ForegroundColor Green

& $python global_search_v37_test.py
if($LASTEXITCODE -ne 0){throw "v3.7 global search security and persistence regression failed"}
Write-Host "v3.7 global search regression passed" -ForegroundColor Green

& $python data_quality_v38_test.py
if($LASTEXITCODE -ne 0){throw 'v3.8 HR data quality permissions and review workflow tests failed'}
Write-Host 'v3.8 HR data quality regression passed' -ForegroundColor Green

& $python performance_v39_test.py
if($LASTEXITCODE -ne 0){throw "v3.9 employee performance appraisal regressions failed"}
Write-Host "v3.9 employee performance role and workflow regression passed" -ForegroundColor Green

& $python performance_growth_v40_test.py
if($LASTEXITCODE -ne 0){throw "v4.0 employee development and feedback regressions failed"}
Write-Host "v4.0 performance development and manager feedback passed" -ForegroundColor Green

& $python performance_actions_v41_test.py
if($LASTEXITCODE -ne 0){throw "v4.1 performance action tracking and review progress regression failed"}
Write-Host "v4.1 action tracking and review progress passed" -ForegroundColor Green

& $python performance_journal_v42_test.py
if($LASTEXITCODE -ne 0){throw "v4.2 performance evidence privacy and goal journal regressions failed"}
Write-Host "v4.2 performance portfolio and goal check-ins passed" -ForegroundColor Green

& $python account_identity_v43_test.py
if($LASTEXITCODE -ne 0){throw "v4.3 identity, work email, account profile editing and developer tier regressions failed"}
Write-Host "v4.3 account profiles, aliases, password safety, roles and audit passed" -ForegroundColor Green

& $python profile_photo_v44_test.py
if($LASTEXITCODE -ne 0){throw "v4.4 profile photo privacy and safe-delete tests failed"}

& $python schema_repair_v441_test.py
if($LASTEXITCODE -ne 0){throw 'v4.5.0 read-only schema audit and repair preflight tests failed'}
Write-Host 'v4.5.0 metadata casing and schema repair safety regression passed' -ForegroundColor Green

& $python mysql_schema_status_test.py
if($LASTEXITCODE -ne 0){throw 'MySQL and SQLite administrator database-status regression failed'}
Write-Host 'Administrator schema status supports SQLite row types and MySQL metadata casing.' -ForegroundColor Green

& $python security_center_v45_test.py
if($LASTEXITCODE -ne 0){throw 'v4.5 account login security, privacy and revocation regression failed'}
Write-Host 'v4.5 account security regression passed' -ForegroundColor Green

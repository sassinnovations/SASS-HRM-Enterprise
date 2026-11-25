"""Offline package check for the merged SASS-HRM-Enterprise-Saritha archive."""
from pathlib import Path
import csv
import re
import sys

ROOT=Path(__file__).resolve().parent.parent
required=[
    'Procfile','railpack.json','railway.toml','web/vercel.json','requirements.txt',
    'web/src/AssetManagement.tsx','web/src/DataQualityImporter.tsx',
    'web/src/ExpensesClaims.tsx','web/src/CandidateLibrary.tsx',
    'server/asset_management.py','server/data_quality_import.py','server/expense_management.py',
    'database/16_ASSET_MANAGEMENT_PROFILES_INSPECTIONS_ADD_ONLY.sql',
    'database/17_HR_DATA_QUALITY_IMPORT_ADD_ONLY.sql',
    'database/18_ADDITIONAL_OPERATIONAL_EVIDENCE_ADD_ONLY.sql',
    'database/19_EXPENSES_CLAIMS_SETTINGS_ADD_ONLY.sql',
    'database/20_RECRUITMENT_JD_LIBRARY_ADD_ONLY.sql',
    'database/21_RECRUITMENT_HR_OPERATIONS_ADD_ONLY.sql',
    'server/job_descriptions.py','web/src/JobDescriptions.tsx',
]
for name in required:
    assert (ROOT/name).is_file(), f'Missing merged feature or hosted configuration: {name}'
core_schema=(ROOT/'server/mysql_schema.sql').read_text(encoding='utf-8')
installation=(ROOT/'database/02_FRESH_INSTALL_ALL_IN_ONE.sql').read_text(encoding='utf-8')
main_app=(ROOT/'server/main.py').read_text(encoding='utf-8')
for content,label in [(core_schema,'server'),(installation,'installer')]:
    tables=set(re.findall(r'(?im)^CREATE TABLE IF NOT EXISTS [`]?([A-Za-z0-9_]+)',content))
    assert len(tables)==288, f'{label} has {len(tables)} tables, expected 288'
assert 'MYSQLHOST' in (ROOT/'server/mysql_backend.py').read_text(encoding='utf-8')
assert 'PUBLIC_APP_URL' in main_app
assert 'healthcheckPath = "/api/ready"' in (ROOT/'railway.toml').read_text(encoding='utf-8')
assert 'openpyxl' in (ROOT/'requirements.txt').read_text(encoding='utf-8')
assert (ROOT/'requirements.txt').read_bytes()==(ROOT/'server/requirements.txt').read_bytes()
assert not list(ROOT.rglob('*.env')), 'Do not package live credentials'
assert not list(ROOT.rglob('*.db')), 'Do not package local personnel data'
allowed_templates = {
    'docs/SASS_HRM_EXCEL_MODULE_COVERAGE_AND_IMPORT_TEMPLATES_2026-11-24.xlsx',
    'docs/SASS_HRM_SERVICE_CATEGORIES_IMPORT_TEMPLATE_2026-11-24.xlsx',
    'docs/SASS_HRM_OFFICES_IMPORT_TEMPLATE_2026-11-24.xlsx',
    'docs/SASS_HRM_HR_TASK_TEMPLATES_IMPORT_TEMPLATE_2026-11-24.xlsx',
}
assert {p.relative_to(ROOT).as_posix() for p in ROOT.rglob('*.xlsx')} <= allowed_templates, 'Do not seed candidates or employees'

from hashlib import sha256
old_hashes=list(csv.DictReader((ROOT/'database/SARITHA_BASELINE_105_TABLE_HASHES.csv').open(newline='',encoding='utf-8')))
coverage=list(csv.DictReader((ROOT/'database/SARITHA_136_NEW_TABLE_MIGRATION_COVERAGE.csv').open(newline='',encoding='utf-8')))
ddl_by_table={name:re.sub(r'\s+',' ',stmt.strip()).lower() for stmt,name in re.findall(r'(?im)^\s*(CREATE TABLE IF NOT EXISTS\s+`?(\w+)`?[^;]*;)',core_schema)}
assert len(old_hashes)==105 and len(coverage)==136
for row in old_hashes:
    assert sha256(ddl_by_table[row['table']].encode()).hexdigest()==row['original_ddl_sha256'], 'Uploaded baseline table changed: '+row['table']
assert len(set(ddl_by_table)-set(r['table'] for r in old_hashes))==183
assert {'jd_import_batches','recruitment_job_descriptions'} <= set(ddl_by_table)
for row in coverage:
    assert row['new_table'] in ddl_by_table
    for script_name in row['additive_migration_files'].split('; '):
        assert script_name and (ROOT/'database'/script_name).exists()

print('PASS Saritha merge: hosted deployment files, 288-table schema, modules, dependencies, no credentials/data')

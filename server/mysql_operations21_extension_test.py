"""Offline guards for the 243 -> 263 SASS INNOVATIONS ENTERPRISE schema migration.

No connection is made to MySQL and no employee/candidate/payload rows are read.
A green result certifies DDL structure and package parity only, not running APIs.
"""
from __future__ import annotations

import hashlib
import re

from mysql_backend import split_ddl
from mysql_feature_schema_integrity import (
    check_file_package, sql_objects, SCHEMA, FRESH, MANUAL,
    OPERATIONS_21_ADD_ONLY, OPERATIONS_21_TABLES, VERIFICATION_22_ADD_ONLY,
)
from schema_audit import split_top_level

previous_schema_sha256 = '495038839c9715fdebc3b8feba9a00c019de210dd3675e5352741ef0f359dc42'
new = OPERATIONS_21_ADD_ONLY.read_text(encoding='utf-8')
canonical = SCHEMA.read_text(encoding='utf-8')
required, indexes, relations = check_file_package()
old_sql = canonical.split('-- SASS HRM — SASS INNOVATIONS ENTERPRISE | migration 21', 1)[0].rstrip()
assert hashlib.sha256((old_sql+'\n').encode()).hexdigest() == previous_schema_sha256, 'Original 243-table DDL changed unexpectedly'
assert len(required) == 272 and sum(map(len, required.values())) == 2242
assert len(indexes) == 331 and len(relations) == 505
assert SCHEMA.read_bytes() == MANUAL.read_bytes()
assert len(split_ddl(new)) == 20
new_tables, new_indexes, new_fk, order = sql_objects(new)
all_tables, _, _, all_order = sql_objects(canonical)
assert order == list(OPERATIONS_21_TABLES) == all_order[all_order.index('recruitment_match_runs'):all_order.index('database_verification_runs')]
assert set(all_tables) - set(new_tables) - {'ai_knowledge_articles','ai_knowledge_scopes','ai_action_proposals','official_work_detail_requests','hrm_work_catalog','hrm_work_catalog_settings'} - set(sql_objects(VERIFICATION_22_ADD_ONLY.read_text(encoding="utf-8"))[0]) == set(sql_objects(old_sql)[0])
assert len(new_indexes) == 41 and len(new_fk) == 50
assert new_indexes <= indexes and new_fk <= relations
assert all(new_tables[t] == all_tables[t] for t in order)
assert all(re.match(r'CREATE TABLE IF NOT EXISTS\s+\w+\s*\(',s,re.I) for s in split_ddl(new))
assert not re.search(r'(?im)^\s*(?:DROP|DELETE|INSERT|REPLACE|ALTER|UPDATE|TRUNCATE)\b',new)
assert not re.search(r'(?im)^\s*(?:DROP|DELETE|INSERT|REPLACE|ALTER|UPDATE|TRUNCATE)\b',FRESH.read_text(encoding='utf-8'))
assert not re.search(r'(?i)ON\s+DELETE\s+CASCADE\b',new)
assert not re.search(r'(?i)\b(?:password_hash|api_secret|fingerprint_template|iris_template|bank_account_number|resume_text)\b',new)
# Referenced field types must agree in MySQL (e.g. BIGINT -> BIGINT, including signedness).
coltypes = {}
for name, statement in all_tables.items():
    part = statement[statement.index('(')+1:statement.rfind(') ENGINE=')]
    fields = {}
    for declaration in split_top_level(part):
        m = re.match(r'\s*`?(\w+)`?\s+(BIGINT|INT|SMALLINT|VARCHAR|CHAR|DATE|DATETIME|DECIMAL|TEXT|LONGTEXT|TINYINT|DOUBLE)\b', declaration,re.I)
        if m:
            fields[m.group(1).lower()] = (m.group(2).upper(), bool(re.search(r'\bUNSIGNED\b',declaration,re.I)))
    coltypes[name] = fields
for table,col,parent,ref in new_fk:
    assert coltypes[table][col] == coltypes[parent][ref],f'{table}.{col} -> {parent}.{ref}'
# JD deletion must still be possible: dependent foreign keys use nullable SET NULL.
for table,col,parent,ref in new_fk:
    if parent == 'recruitment_job_descriptions':
        assert col == 'job_description_id' and ref == 'id'
        assert re.search(r'job_description_id\s+BIGINT\s+NULL',new_tables[table],re.I)
        assert re.search(r'FOREIGN KEY\s*\(job_description_id\)\s+REFERENCES\s+recruitment_job_descriptions\s*\(id\)\s+ON\s+DELETE\s+SET\s+NULL',new_tables[table],re.I)
# Explicit coverage includes candidate match scoring and stocktake reconciliation.
for name, expected_columns in {
    'recruitment_match_runs': {'job_description_id','scoring_version','requested_by'},
    'recruitment_match_results': {'candidate_id','match_score','evidence_summary'},
    'candidate_shortlist_decisions': {'candidate_id','job_description_id','decided_by'},
    'employee_employment_verification_requests': {'employee_id','request_status','verified_by'},
    'payroll_preflight_validation_results': {'pay_run_id','rule_code','severity'},
    'asset_stocktake_items': {'asset_id','session_id','observed_condition'},
    'integration_import_row_errors': {'batch_id','source_row_number','error_code'},
}.items():
    assert expected_columns <= required[name],name
print('PASS: original 243 table definitions preserved (SHA-256), +20 add-only DDLs')
print('PASS: 272 tables, 2242 columns, 331 indexes, 505 total FKs; 50 new FK types verified')
print('PASS: JD deletion preserved, no seed/data writes, no secret/biometric/resume columns')

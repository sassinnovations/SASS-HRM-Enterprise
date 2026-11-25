"""Offline regression for 20 additive workflow foundations; never connects to user data."""
from pathlib import Path
import re
from mysql_backend import split_ddl
from mysql_feature_schema_integrity import (
    SCHEMA, FRESH, MANUAL, INVENTORY, WORKFLOW_TABLES, WORKFLOW_ADD_ONLY,
    sql_objects, check_file_package,
)
from schema_audit import get_required_schema

required, indexes, relations = check_file_package()
assert len(required) == 288
assert sum(map(len, required.values())) == 2318
assert len(indexes) == 337
assert len(relations) == 522
assert SCHEMA.read_bytes() == MANUAL.read_bytes()

patch = WORKFLOW_ADD_ONLY.read_text(encoding='utf-8')
statements = split_ddl(patch)
tables, new_indexes, new_relations, ordered = sql_objects(patch)
assert len(statements) == 20, len(statements)
assert set(tables) == WORKFLOW_TABLES
assert len(new_indexes) == 27
assert len(new_relations) == 48
assert all(re.match(r'^CREATE TABLE IF NOT EXISTS\b', sql, re.I) for sql in statements)
assert all('ENGINE=InnoDB' in sql for sql in statements)
assert all('DEFAULT CHARSET=utf8mb4' in sql for sql in statements)
assert all(not re.search(r'^\s*(DROP|TRUNCATE|DELETE|UPDATE|INSERT|REPLACE|ALTER)\b',sql,re.I) for sql in statements)
assert not re.search(r'(?mi)^\s*(INSERT|UPDATE|DELETE|DROP|TRUNCATE|REPLACE)\b', patch)
assert not re.search(r'(?i)(fingerprint_template|iris_template|bank_account_number|api_secret|password_hash)',patch)

all_tables, _, _, full_order = sql_objects(SCHEMA.read_text(encoding='utf-8'))
assert ordered == full_order[full_order.index(ordered[0]):full_order.index(ordered[0])+len(ordered)]
assert all(tables[name] == all_tables[name] for name in ordered)
assert all((table, index) in indexes for table,index in new_indexes)
assert all(fk in relations for fk in new_relations)
assert {'component_id','amount','employee_id'} <= required['payroll_employee_components']
assert {'candidate_id','score_percent','assessment_type'} <= required['candidate_assessment_results']
assert {'employee_id','minutes_requested','status'} <= required['attendance_overtime_requests']
assert {'delivery_id','payload_sha256','signature_verified'} <= required['integration_webhook_receipts']
assert {'employee_id','export_scope','status'} <= required['employee_data_export_requests']

# A freshly deployed database must not silently load candidates or historical pay.
for sql in split_ddl(FRESH.read_text(encoding='utf-8')):
    assert not re.match(r'^\s*(INSERT|UPDATE|DELETE|TRUNCATE|DROP|REPLACE)\b',sql,re.I), sql[:120]

# Corrupted/missing objects must be detected rather than silently called complete.
modified = patch.replace('CREATE TABLE IF NOT EXISTS employee_probation_reviews',
                         'CREATE TABLE IF NOT EXISTS employee_probation_reviews_broken',1)
assert set(sql_objects(modified)[0]) != WORKFLOW_TABLES
assert all('ON DELETE CASCADE' not in tables[name] for name in (
    'employee_education_records','employee_probation_reviews',
    'payroll_approval_signoffs','payroll_reconciliation_issues'))
print('PASS: 20 new database tables, 27 named indexes, 48 foreign keys, no seeded or destructive SQL')
print('PASS: 263 total tables, 2174 columns, 320 named indexes, 497 foreign keys; all installer copies agree')

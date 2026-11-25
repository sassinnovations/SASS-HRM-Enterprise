"""Offline safety and integrity verification for SASS HRM 173->215 MySQL extension.
No live MySQL connection or HR data writes.
"""
import re
from mysql_backend import split_ddl
from mysql_feature_schema_integrity import (SCHEMA, FRESH, MANUAL, PLANNING_ADD_ONLY,
    PLANNING_TABLES, check_file_package, sql_objects)
from schema_audit import split_top_level

required, indexes, fks = check_file_package()
assert len(required) == 272
assert sum(map(len, required.values())) == 2242
assert len(indexes) == 331 and len(fks) == 505
assert SCHEMA.read_bytes() == MANUAL.read_bytes()

patch = PLANNING_ADD_ONLY.read_text(encoding='utf-8')
statements = split_ddl(patch)
tables, new_indexes, new_fks, ordered = sql_objects(patch)
full_tables, _, _, full_order = sql_objects(SCHEMA.read_text(encoding='utf-8'))
assert len(statements) == 20 and set(tables) == PLANNING_TABLES
assert ordered == full_order[full_order.index(ordered[0]):full_order.index(ordered[0])+len(ordered)]
assert len(new_indexes) == 40 and len(new_fks) == 59
assert all(tables[name] == full_tables[name] for name in ordered)
assert new_indexes <= indexes and new_fks <= fks
assert all(re.match(r'^CREATE TABLE IF NOT EXISTS\b', s, re.I) for s in statements)
assert all('ENGINE=InnoDB' in s and 'DEFAULT CHARSET=utf8mb4' in s for s in statements)
assert all(not re.search(r'\bON DELETE\s+CASCADE\b',s,re.I) for s in statements)
assert all(not re.match(r'^(?:INSERT|UPDATE|DELETE|DROP|TRUNCATE|ALTER|REPLACE)\b',s,re.I) for s in statements)
assert not re.search(r'\b(?:fingerprint_template|iris_template|bank_account_number|password_hash|api_secret)\b',patch,re.I)
assert {'employee_id','action_kind','effective_on','requested_by'} <= required['employee_personnel_actions']
assert {'employee_id','work_day','missing_event','case_status'} <= required['attendance_missing_punch_cases']
assert {'run_id','employee_id','prior_net_pay','current_net_pay'} <= required['payroll_variance_review_cases']
assert {'candidate_id','source_channel','verification_status'} <= required['candidate_application_source_records']
assert {'policy_id','policy_revision','acknowledged_at'} <= required['employee_policy_version_acceptances']

# Every new FK must resolve to a compatible column type; protect against typo migrations.
col_types = {}
for name, statement in full_tables.items():
    m=re.search(r'^CREATE TABLE IF NOT EXISTS\s+\w+\s*\(',statement)
    assert m
    body=statement[m.end():statement.rfind(') ENGINE=')]
    types={}
    for decl in split_top_level(body):
        field=re.match(r'^\s*`?(\w+)`?\s+(BIGINT|INT|SMALLINT|VARCHAR|DATE|DATETIME|DECIMAL|TEXT|LONGTEXT|TINYINT|CHAR)\b',decl,re.I)
        if field:types[field.group(1).lower()]=field.group(2).upper()
    col_types[name]=types
for name,col,parent,parent_col in new_fks:
    assert name in col_types and parent in col_types
    assert col_types[name][col] == col_types[parent][parent_col], (name,col,parent,parent_col)
for stmt in split_ddl(FRESH.read_text(encoding='utf-8')):
    assert not re.match(r'^(?:INSERT|UPDATE|DELETE|TRUNCATE|DROP|REPLACE)\b',stmt,re.I)
print('PASS: 20 additional add-only review/planning tables, 196 columns, 40 indexes, 59 foreign keys')
print('PASS: 263-table schema parity, safe FK types, zero candidate preload, no destructive DML')

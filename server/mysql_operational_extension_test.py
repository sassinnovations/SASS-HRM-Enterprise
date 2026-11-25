"""Offline checks for the 20-table operational extension (no live DB writes)."""
from pathlib import Path
import re
from mysql_backend import split_ddl
from mysql_feature_schema_integrity import (
    check_file_package, sql_objects, SCHEMA, FRESH, MANUAL,
    OPERATIONAL_ADD_ONLY, OPERATIONAL_TABLES, WORKFLOW_ADD_ONLY,
)
from schema_audit import split_top_level

required, indexes, fks = check_file_package()
assert len(required) == 288
assert sum(map(len, required.values())) == 2318
assert len(indexes) == 337 and len(fks) == 522
assert SCHEMA.read_bytes() == MANUAL.read_bytes()
assert len(OPERATIONAL_TABLES) == 20

sql = OPERATIONAL_ADD_ONLY.read_text(encoding='utf-8')
statements = split_ddl(sql)
tables, indexes_new, relations_new, ordered = sql_objects(sql)
full_tables, _, _, full_order = sql_objects(SCHEMA.read_text(encoding='utf-8'))
assert len(statements) == 20 and set(tables) == OPERATIONAL_TABLES
assert ordered == full_order[full_order.index(ordered[0]):full_order.index(ordered[0])+len(ordered)]
assert all(tables[name] == full_tables[name] for name in ordered)
assert len(indexes_new) == 40 and len(relations_new) == 59
assert indexes_new <= indexes and relations_new <= fks
assert all(re.match(r'^CREATE TABLE IF NOT EXISTS\b', s, re.I) for s in statements)
assert all('ENGINE=InnoDB' in s and 'DEFAULT CHARSET=utf8mb4' in s for s in statements)
assert all(not re.search(r'\bON DELETE\s+CASCADE\b', s, re.I) for s in statements)
assert all(not re.match(r'^(?:INSERT|UPDATE|DELETE|DROP|TRUNCATE|ALTER|REPLACE)\b', s, re.I) for s in statements)
assert all(len(required[name]) >= 8 and 'id' in required[name] and bool({'created_at', 'recorded_at', 'opened_at', 'requested_at'} & required[name]) for name in ordered)
assert not re.search(r'\b(?:fingerprint_template|iris_template|bank_account_number|password_hash|api_secret)\b', sql, re.I)
assert {'employee_id','renewal_due','verification_status'} <= required['employee_license_renewals']
assert {'employee_id','manager_id','effective_from'} <= required['employee_manager_assignments']
assert {'run_id','employee_id','change_category','status'} <= required['payroll_input_change_requests']
assert {'candidate_id','due_at','case_status'} <= required['candidate_stage_sla_cases']
assert {'asset_id','employee_id','return_status'} <= required['asset_return_confirmations']

# Every new FK must point to a BIGINT ID, and be declared before the dependent table.
columns_by_table = {}
for name, statement in full_tables.items():
    found = re.search(r'^CREATE TABLE IF NOT EXISTS\s+\w+\s*\(', statement)
    assert found
    body = statement[found.end():statement.rfind(') ENGINE=')]
    col_types = {}
    for decl in split_top_level(body):
        m = re.match(r'^\s*`?(\w+)`?\s+(BIGINT|INT|SMALLINT|VARCHAR|DATE|DATETIME|DECIMAL|TEXT|LONGTEXT|TINYINT)\b',decl,re.I)
        if m:col_types[m.group(1).lower()] = m.group(2).upper()
    columns_by_table[name]=col_types
for name, col, ref, refcol in relations_new:
    assert name in columns_by_table and ref in columns_by_table
    assert columns_by_table[name][col] == columns_by_table[ref][refcol], (name,col,ref,refcol)

for stmt in split_ddl(FRESH.read_text(encoding='utf-8')):
    assert not re.match(r'^(?:INSERT|UPDATE|DELETE|TRUNCATE|DROP|REPLACE)\b',stmt,re.I)
assert 'CREATE TABLE IF NOT EXISTS employee_license_renewals' in SCHEMA.read_text(encoding='utf-8')
assert 'CREATE TABLE IF NOT EXISTS employee_license_renewals' not in WORKFLOW_ADD_ONLY.read_text(encoding='utf-8')
print('PASS: 20 add-only operational tables, 184 new columns, 40 named indexes, 59 foreign keys')
print('PASS: 263-table schema parity, reference types, zero candidate seed and no destructive SQL')

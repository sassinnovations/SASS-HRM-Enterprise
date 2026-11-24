"""Offline SASS HRM 193 -> 215 MySQL controls extension: safety and compatibility.
This test cannot certify an actual MySQL installation or application workflows.
"""
import re
from mysql_backend import split_ddl
from mysql_feature_schema_integrity import (
    CONTROL_ADD_ONLY, CONTROL_TABLES, SCHEMA, FRESH, MANUAL,
    check_file_package, sql_objects,
)
from schema_audit import split_top_level

required, indexes, fks = check_file_package()
assert len(required) == 270 and sum(map(len,required.values())) == 2226
assert len(indexes) == 329 and len(fks) == 504
assert SCHEMA.read_bytes() == MANUAL.read_bytes()

sql=CONTROL_ADD_ONLY.read_text(encoding='utf-8')
statements=split_ddl(sql)
tables, new_indexes, new_fks, ordered=sql_objects(sql)
full_tables, _, _, full_order=sql_objects(SCHEMA.read_text(encoding='utf-8'))
assert len(statements)==20 and set(tables)==CONTROL_TABLES
assert ordered==full_order[full_order.index(ordered[0]):full_order.index(ordered[0])+len(ordered)]
assert len(new_indexes)==40 and len(new_fks)==66
assert all(tables[name]==full_tables[name] for name in ordered)
assert new_indexes <= indexes and new_fks <= fks
assert all(re.match(r'^CREATE TABLE IF NOT EXISTS\b',x,re.I) for x in statements)
assert all('ENGINE=InnoDB' in x and 'DEFAULT CHARSET=utf8mb4' in x for x in statements)
assert not re.search(r'(?mi)^\s*(DROP|TRUNCATE|ALTER|INSERT|UPDATE|DELETE|REPLACE)\b',sql)
assert not re.search(r'(?i)\b(fingerprint_template|iris_template|bank_account_number|password_hash|api_secret)\b',sql)
assert all(not re.search(r'\bON DELETE\s+CASCADE\b',x,re.I) for x in statements)
assert {'employee_id','document_category','expires_on'} <= required['employee_work_authorization_documents']
assert {'device_id','fault_code','case_status'} <= required['attendance_device_maintenance_cases']
assert {'run_id','employee_id','hold_status'} <= required['payroll_employee_payment_holds']
assert {'candidate_id','job_id','verification_status'} <= required['recruitment_candidate_document_checks']
assert {'asset_id','maintenance_kind','request_status'} <= required['asset_maintenance_requests']

# Check each FK links like-typed columns: no dangling/dependency-misaligned references.
types={}
for name, stmt in full_tables.items():
    head=re.search(r'^CREATE TABLE IF NOT EXISTS\s+\w+\s*\(',stmt)
    assert head
    body=stmt[head.end():stmt.rfind(') ENGINE=')]
    columns={}
    for decl in split_top_level(body):
        match=re.match(r'^\s*`?(\w+)`?\s+(BIGINT|INT|SMALLINT|VARCHAR|CHAR|DATE|DATETIME|DECIMAL|TEXT|LONGTEXT|TINYINT|DOUBLE)\b',decl,re.I)
        if match:columns[match.group(1).lower()]=match.group(2).upper()
    types[name]=columns
for name,col,parent,parent_col in new_fks:
    assert parent in types and parent_col in types[parent],(name,parent,parent_col)
    assert col in types[name] and types[name][col]==types[parent][parent_col],(name,col,parent,parent_col)
for stmt in split_ddl(FRESH.read_text(encoding='utf-8')):
    assert not re.match(r'^\s*(INSERT|UPDATE|DELETE|TRUNCATE|DROP|REPLACE)\b',stmt,re.I)
print('PASS: 20 new control tables, 198 columns, 40 indexes, 66 foreign keys; MySQL definitions and installation SQL agree')
print('PASS: zero candidate seed; no existing rows mutated by the migration')

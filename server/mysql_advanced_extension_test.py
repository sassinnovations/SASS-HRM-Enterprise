"""Offline checks for 15 additional, additive MySQL tables. Does not connect to live data."""
from pathlib import Path
import re
from mysql_backend import split_ddl
from mysql_feature_schema_integrity import (
    check_file_package, sql_objects, SCHEMA, EXTENSION_ADD_ONLY, EXTENSION_TABLES
)
from schema_audit import get_required_schema
required, indexes, relations = check_file_package()
assert len(required) == 288
assert sum(map(len, required.values())) == 2318
migration = EXTENSION_ADD_ONLY.read_text(encoding='utf-8')
statements = split_ddl(migration)
assert len(statements) == 15
assert all(re.match(r'^CREATE TABLE IF NOT EXISTS ', s, re.I) for s in statements)
assert all('ENGINE=InnoDB' in s for s in statements)
assert all(not re.match(r'^(?:DROP|TRUNCATE|DELETE|INSERT|UPDATE|REPLACE|ALTER)\b',s,re.I) for s in statements)
assert not any(x in migration.lower() for x in ['fingerprint_template', 'iris_template', 'bank_account_number', 'bank_routing_number'])
tables, named_indexes, fks, ordered = sql_objects(migration)
assert set(tables) == EXTENSION_TABLES
assert named_indexes <= indexes
assert fks <= relations
assert len(fks) >= 15
for name in ordered:
    assert name in required
assert {'employee_id', 'contact_name', 'phone'} <= required['employee_emergency_contacts']
assert {'device_code', 'device_type', 'key_reference'} <= required['attendance_device_registry']
assert {'run_id', 'currency', 'status'} <= required['payroll_disbursement_batches']
assert {'candidate_id', 'decision'} <= required['candidate_consent_events']
assert {'resource_type', 'legal_hold', 'enabled'} <= required['data_retention_rules']
print('PASS: advanced MySQL migration, 15 additive tables, no seeded records or destructive SQL')

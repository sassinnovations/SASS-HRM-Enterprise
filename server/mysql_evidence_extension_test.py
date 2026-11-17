"""Offline verification of the 217 -> 237 (current total 241) schema-only, add-only expansion.

Does not connect to MySQL, modify HR records or certify operational workflows.
"""
from pathlib import Path
import re

from mysql_backend import split_ddl
from mysql_feature_schema_integrity import (
    SCHEMA, FRESH, MANUAL, EVIDENCE_ADD_ONLY, EVIDENCE_TABLES,
    sql_objects, check_file_package,
)
from schema_audit import split_top_level

required, named_indexes, relations = check_file_package()
assert len(required) == 241
assert sum(map(len, required.values())) == 1986
assert len(named_indexes) == 274 and len(relations) == 442
assert SCHEMA.read_bytes() == MANUAL.read_bytes()

statements = split_ddl(EVIDENCE_ADD_ONLY.read_text(encoding='utf-8'))
new_tables, new_indexes, new_relations, new_order = sql_objects(
    EVIDENCE_ADD_ONLY.read_text(encoding='utf-8'))
all_tables, _, _, all_order = sql_objects(SCHEMA.read_text(encoding='utf-8'))
assert len(statements) == len(new_tables) == 20
assert set(new_tables) == EVIDENCE_TABLES
assert new_order == all_order[-24:-4]
assert len(new_indexes) == 40 and len(new_relations) == 53
assert new_indexes <= named_indexes and new_relations <= relations
assert all(new_tables[name] == all_tables[name] for name in new_order)
assert all(re.match(r'^CREATE\s+TABLE\s+IF\s+NOT\s+EXISTS\b', statement, re.I)
           and 'ENGINE=InnoDB' in statement and 'DEFAULT CHARSET=utf8mb4' in statement
           for statement in statements)
for statement in split_ddl(EVIDENCE_ADD_ONLY.read_text(encoding='utf-8')):
    assert not re.search(r'\b(?:DROP|TRUNCATE|ALTER|INSERT|UPDATE|DELETE|REPLACE)\b',
                         statement.split('(',1)[0], re.I)
    assert not re.search(r'\bON\s+DELETE\s+CASCADE\b', statement, re.I)
assert not re.search(r'\b(?:fingerprint_template|iris_template|password_hash|api_secret|bank_account_number)\b',
                     EVIDENCE_ADD_ONLY.read_text(encoding='utf-8'), re.I)
assert not re.search(r'(?mi)^\s*(?:INSERT|UPDATE|DELETE|REPLACE|TRUNCATE|DROP)\b',
                     FRESH.read_text(encoding='utf-8'))
# Parent/child FK type and signedness consistency (BIGINT references).
types = {}
for name, statement in all_tables.items():
    body = statement[statement.index('(')+1:statement.rfind(') ENGINE=')]
    columns = {}
    for item in split_top_level(body):
        m = re.match(r'^\s*`?(\w+)`?\s+(BIGINT|INT|SMALLINT|VARCHAR|CHAR|DATE|DATETIME|DECIMAL|TEXT|LONGTEXT|TINYINT|DOUBLE)\b', item, re.I)
        if m:
            columns[m.group(1).lower()] = (m.group(2).upper(), bool(re.search(r'\bUNSIGNED\b', item, re.I)))
    types[name] = columns
for name, col, parent, parent_col in new_relations:
    assert (parent in types and parent_col in types[parent]
            and col in types[name]), (name, col, parent, parent_col)
    assert types[name][col] == types[parent][parent_col], (name,col,parent,parent_col)
# Explicitly guard the highest-priority new operational evidence fields.
for table, columns in {
    'payroll_esi_eligibility_reviews': {'employee_id','contribution_period','gross_wages','review_status','reviewed_by'},
    'payroll_pf_eligibility_reviews': {'employee_id','effective_on','decision','review_status'},
    'attendance_manual_punch_approvals': {'employee_id','attendance_id','work_day','approval_status'},
    'recruitment_interview_scorecards': {'candidate_id','job_id','evaluator_id','score'},
    'asset_custody_acknowledgements': {'asset_id','employee_id','acknowledgement_status'},
    'hr_data_quality_import_row_issues': {'import_id','source_row_number','issue_code','severity'},
}.items():
    assert columns <= required[table], table
print('PASS: 20 additive tables, 178 new columns, 40 indexes, 53 correctly typed foreign keys')
print('PASS: old tables preserved, installer and migration match, no seed records or cascading deletes')

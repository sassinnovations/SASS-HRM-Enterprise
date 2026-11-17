"""Read-only verification for the complete SASS HRM Enterprise MySQL schema.

Offline mode compares bundled installers, 241-table inventory, indexes, foreign keys,
and backend-owned declarations. Live mode additionally queries INFORMATION_SCHEMA;
no user/candidate/payroll records are read or changed.
"""
from __future__ import annotations

import argparse
import csv
import os
import re
import sys
from pathlib import Path

from mysql_backend import split_ddl
from schema_audit import compare, database_inventory, field, get_required_schema, source_coverage

ROOT = Path(__file__).resolve().parent.parent
SCHEMA = ROOT / 'server/mysql_schema.sql'
FRESH = ROOT / 'database/02_FRESH_INSTALL_ALL_IN_ONE.sql'
MANUAL = ROOT / 'database/01_application_schema.sql'
INVENTORY = ROOT / 'database/ALL_MYSQL_TABLES.csv'
ADD_ONLY = ROOT / 'database/09_MISSING_MODULE_TABLES_ADD_ONLY.sql'
EXTENSION_ADD_ONLY = ROOT / 'database/10_ADVANCED_HR_MODULES_ADD_ONLY.sql'
HIRING_STAGE_ADD_ONLY = ROOT / 'database/11_HIRING_STAGE_SETTINGS_ADD_ONLY.sql'
WORKFLOW_ADD_ONLY = ROOT / 'database/12_ADDITIONAL_WORKFLOW_TABLES_ADD_ONLY.sql'
OPERATIONAL_ADD_ONLY = ROOT / 'database/13_ADDITIONAL_OPERATIONAL_TABLES_ADD_ONLY.sql'
PLANNING_ADD_ONLY = ROOT / 'database/14_REVIEW_AND_PLANNING_TABLES_ADD_ONLY.sql'
CONTROL_ADD_ONLY = ROOT / 'database/15_ADDITIONAL_CONTROL_TABLES_ADD_ONLY.sql'
ASSET_ADD_ONLY = ROOT / 'database/16_ASSET_MANAGEMENT_PROFILES_INSPECTIONS_ADD_ONLY.sql'
QUALITY_IMPORT_ADD_ONLY = ROOT / 'database/17_HR_DATA_QUALITY_IMPORT_ADD_ONLY.sql'
EVIDENCE_ADD_ONLY = ROOT / 'database/18_ADDITIONAL_OPERATIONAL_EVIDENCE_ADD_ONLY.sql'
EXPENSES_ADD_ONLY = ROOT / 'database/19_EXPENSES_CLAIMS_SETTINGS_ADD_ONLY.sql'
EXPENSE_TABLES = ('expense_policy_settings','expense_claim_details','expense_claim_events','expense_reimbursement_records')
EVIDENCE_TABLES = frozenset({
 'employee_contact_change_reviews', 'employee_employment_letter_register',
 'employee_exit_clearance_signoffs', 'employee_hr_case_consents',
 'attendance_manual_punch_approvals', 'attendance_device_clock_drift_logs',
 'leave_supporting_document_reviews', 'timesheet_approval_batches',
 'payroll_esi_eligibility_reviews', 'payroll_pf_eligibility_reviews',
 'payroll_offcycle_run_requests', 'payroll_payment_exception_cases',
 'recruitment_job_skill_requirements', 'recruitment_interview_scorecards',
 'recruitment_offer_acceptance_events', 'recruitment_candidate_talent_tags',
 'asset_custody_acknowledgements', 'asset_disposal_approvals',
 'hr_data_quality_import_row_issues', 'hr_data_quality_import_approval_reviews',
})
CONTROL_TABLES = frozenset({
    'employee_work_authorization_documents',
    'employee_probation_action_items',
    'employee_contract_renewal_requests',
    'employee_assignment_handover_checklists',
    'attendance_device_maintenance_cases',
    'attendance_roster_change_reviews',
    'leave_return_to_work_confirmations',
    'attendance_exception_approval_steps',
    'payroll_employee_payment_holds',
    'payroll_retro_adjustment_requests',
    'payroll_payslip_delivery_receipts',
    'payroll_month_end_checkpoints',
    'recruitment_screening_templates',
    'recruitment_screening_responses',
    'recruitment_candidate_document_checks',
    'recruitment_stage_escalation_cases',
    'compliance_evidence_register',
    'privacy_data_correction_requests',
    'integration_field_mapping_revisions',
    'asset_maintenance_requests',
})
PLANNING_TABLES = frozenset({
    'employee_personnel_actions','employee_delegation_assignments','workforce_headcount_plans','employee_internal_mobility_applications',
    'attendance_missing_punch_cases','attendance_break_logs','attendance_shift_swap_requests','leave_encashment_requests',
    'payroll_variance_review_cases','payroll_funding_approval_requests','payroll_tax_residency_declarations','payroll_recovery_schedules',
    'candidate_application_source_records','recruitment_interview_panel_members','recruitment_offer_approval_steps','recruitment_candidate_contact_queue',
    'employee_policy_version_acceptances','employee_skill_gap_reviews','hr_ticket_escalation_records','integration_connector_health_results'
})
OPERATIONAL_TABLES = frozenset({'employee_license_renewals', 'employee_work_authorization_reviews', 'employee_manager_assignments', 'employee_transfer_requests', 'attendance_roster_publications', 'attendance_remote_work_reviews', 'leave_blackout_periods', 'leave_balance_reconciliations', 'payroll_input_change_requests', 'payroll_deduction_review_cases', 'payroll_cost_center_allocations', 'payroll_tax_document_checks', 'recruitment_requisition_requests', 'candidate_stage_sla_cases', 'candidate_reference_check_reviews', 'candidate_offer_document_reviews', 'training_certificate_renewals', 'employee_training_compliance_cases', 'asset_return_confirmations', 'compliance_control_attestations'})
WORKFLOW_TABLES = frozenset({'employee_education_records', 'employee_probation_reviews', 'employee_position_assignments', 'employee_exit_interviews', 'attendance_overtime_requests', 'attendance_shift_change_requests', 'attendance_exception_reviews', 'leave_carryforward_events', 'payroll_component_catalog', 'payroll_employee_components', 'payroll_reconciliation_issues', 'payroll_approval_signoffs', 'candidate_assessment_results', 'candidate_interview_feedback', 'candidate_offer_approvals', 'candidate_duplicate_review_cases', 'data_access_review_cases', 'integration_webhook_receipts', 'retention_hold_requests', 'employee_data_export_requests'})
EXTENSION_TABLES = frozenset({'employee_emergency_contacts', 'employee_certifications', 'employee_job_history', 'employment_contract_versions', 'attendance_device_registry', 'attendance_device_employee_links', 'leave_accrual_ledger', 'payroll_disbursement_batches', 'payroll_disbursement_items', 'payroll_statutory_obligations', 'candidate_consent_events', 'recruitment_job_approvals', 'integration_sync_runs', 'integration_sync_errors', 'data_retention_rules'})
LEGACY_TABLES = frozenset({
    'account_login_events', 'account_signup_requests', 'attendance_capture_events',
    'attendance_photo_evidence', 'attendance_device_nonces'
})
TABLE_PATTERN = re.compile(r'^CREATE\s+TABLE\s+IF\s+NOT\s+EXISTS\s+`?(\w+)`?\s*\(', re.I)
INDEX_PATTERN = re.compile(r'^CREATE\s+(?:UNIQUE\s+)?INDEX\s+`?(\w+)`?\s+ON\s+`?(\w+)`?\s*\(', re.I)
INLINE_INDEX_PATTERN = re.compile(r'\b(?:UNIQUE\s+)?(?:KEY|INDEX)\s+`?([a-z_][a-z_0-9]*)`?\s*\(', re.I)
FK_PATTERN = re.compile(
    r'\bFOREIGN\s+KEY\s*\(\s*`?(\w+)`?\s*\)\s*'
    r'REFERENCES\s+`?(\w+)`?\s*\(\s*`?(\w+)`?\s*\)', re.I,
)


def sql_objects(contents: str):
    tables, indexes, relations, ordered = {}, set(), set(), []
    for sql in split_ddl(contents):
        match = TABLE_PATTERN.match(sql)
        if match:
            name = match.group(1).lower()
            if name in tables:
                raise ValueError(f'Duplicate declaration: {name}')
            tables[name] = sql
            ordered.append(name)
            for index in INLINE_INDEX_PATTERN.findall(sql):
                indexes.add((name, index.lower()))
            for column, parent, referenced in FK_PATTERN.findall(sql):
                relations.add((name, column.lower(), parent.lower(), referenced.lower()))
        else:
            match = INDEX_PATTERN.match(sql)
            if match:
                indexes.add((match.group(2).lower(), match.group(1).lower()))
    return tables, indexes, relations, ordered


def check_file_package():
    schema = SCHEMA.read_text(encoding='utf-8')
    required = get_required_schema()
    if (issues := source_coverage(required)):
        raise ValueError('Backend table declarations not covered by MySQL: ' + '; '.join(issues[:10]))
    if len(required) != 241 or sum(map(len, required.values())) != 1986:
        raise ValueError('Release contract changed; review/refresh 241-table, 1986-column inventory')
    if MANUAL.read_bytes() != SCHEMA.read_bytes():
        raise ValueError('database/01_application_schema.sql is out of sync with server/mysql_schema.sql')

    tables, indexes, foreign_keys, ordered = sql_objects(schema)
    fresh_sql = FRESH.read_text(encoding='utf-8')
    fresh_tables, fresh_indexes, fresh_foreign_keys, fresh_ordered = sql_objects(fresh_sql)
    if tables != fresh_tables or indexes != fresh_indexes or foreign_keys != fresh_foreign_keys or ordered != fresh_ordered:
        raise ValueError('Fresh install SQL does not include the exact current backend tables/indexes/FKs in their dependency order')
    for statement in split_ddl(fresh_sql):
        if re.match(r'^(?:DROP|TRUNCATE|DELETE|REPLACE|INSERT|UPDATE)\b', statement, re.I):
            raise ValueError('Fresh installation SQL must contain schema objects only, with no seeded records or destructive DML')
    if not re.search(r'\bCREATE\s+DATABASE\s+IF\s+NOT\s+EXISTS\b', fresh_sql, re.I):
        raise ValueError('Fresh install must contain an explicit opt-in database CREATE statement')

    legacy_tables, _, legacy_relations, _ = sql_objects(ADD_ONLY.read_text(encoding='utf-8'))
    if set(legacy_tables) != LEGACY_TABLES or any(legacy_tables[name] != tables[name] for name in LEGACY_TABLES):
        raise ValueError('Five-table additive legacy patch does not match the authoritative definitions')
    if not legacy_relations <= foreign_keys:
        raise ValueError('Legacy patch uses inconsistent foreign keys')

    hiring_sql=HIRING_STAGE_ADD_ONLY.read_text(encoding='utf-8')
    hiring_tables, hiring_indexes, hiring_foreign_keys, _ = sql_objects(hiring_sql)
    if set(hiring_tables) != {'hiring_stage_settings'} or hiring_tables['hiring_stage_settings'] != tables['hiring_stage_settings']:
        raise ValueError('Hiring-stage settings additive SQL must match the canonical schema')
    if not hiring_foreign_keys <= foreign_keys or not hiring_indexes <= indexes:
        raise ValueError('Hiring-stage settings migration has inconsistent schema relationships')
    if len(split_ddl(hiring_sql)) != 1:
        raise ValueError('Hiring-stage settings patch must create exactly one table and have no data writes')

    # Historical extension migrations must be compared against the schema prefix
    # that existed BEFORE the new 20-table control extension.
    control_start = ordered.index('employee_work_authorization_documents')
    prior_order = ordered[:control_start]
    # The versioned advanced-data patch contains ONLY the 15 new tables, with
    # definitions byte-for-byte equal to the authoritative server schema.
    extension_statements = split_ddl(EXTENSION_ADD_ONLY.read_text(encoding='utf-8'))
    extension_tables, extension_indexes, extension_fks, extension_order = sql_objects(
        EXTENSION_ADD_ONLY.read_text(encoding='utf-8'))
    if set(extension_tables) != EXTENSION_TABLES or extension_order != prior_order[-len(PLANNING_TABLES)-len(OPERATIONAL_TABLES)-len(WORKFLOW_TABLES)-len(EXTENSION_TABLES):-len(PLANNING_TABLES)-len(OPERATIONAL_TABLES)-len(WORKFLOW_TABLES)]:
        raise ValueError('Advanced HR migration does not contain exactly the expected 15 new tables')
    if any(extension_tables[name] != tables[name] for name in EXTENSION_TABLES):
        raise ValueError('Advanced HR migration definitions differ from canonical schema')
    if not extension_indexes <= indexes or not extension_fks <= foreign_keys:
        raise ValueError('Advanced HR migration contains inconsistent indexes or FK definitions')
    if len(extension_statements) != len(EXTENSION_TABLES) or any(not TABLE_PATTERN.match(s) for s in extension_statements):
        raise ValueError('Advanced HR patch must contain CREATE TABLE IF NOT EXISTS statements only')
    forbidden = re.compile(r'^(?:DROP|TRUNCATE|DELETE|UPDATE|INSERT|REPLACE|ALTER)\b', re.I)
    if any(forbidden.search(stmt) for stmt in extension_statements):
        raise ValueError('Advanced HR patch must never contain destructive DDL or data writes')
    # Exactly the 20 additional workflow tables, in dependency-safe order, with
    # definitions identical to the backend and no data manipulation.
    workflow_sql = WORKFLOW_ADD_ONLY.read_text(encoding='utf-8')
    workflow_statements = split_ddl(workflow_sql)
    workflow_tables, workflow_indexes, workflow_fks, workflow_order = sql_objects(workflow_sql)
    if set(workflow_tables) != WORKFLOW_TABLES or workflow_order != prior_order[-len(PLANNING_TABLES)-len(OPERATIONAL_TABLES)-len(WORKFLOW_TABLES):-len(PLANNING_TABLES)-len(OPERATIONAL_TABLES)]:
        raise ValueError('Workflow extension does not contain exactly the expected 20 new tables')
    if any(workflow_tables[name] != tables[name] for name in WORKFLOW_TABLES):
        raise ValueError('Workflow migration definitions differ from canonical schema')
    if not workflow_indexes <= indexes or not workflow_fks <= foreign_keys:
        raise ValueError('Workflow migration indexes or foreign keys are inconsistent')
    if len(workflow_statements) != len(WORKFLOW_TABLES) or any(not TABLE_PATTERN.match(stmt) for stmt in workflow_statements):
        raise ValueError('Workflow patch must contain only 20 CREATE TABLE IF NOT EXISTS statements')
    if any(forbidden.search(stmt) for stmt in workflow_statements):
        raise ValueError('Workflow patch cannot contain destructive DDL or data manipulation')
    if any('ENGINE=InnoDB' not in stmt for stmt in workflow_statements):
        raise ValueError('Workflow tables must use InnoDB')
    # Additional operational review tables are a separate, additive migration.
    operational_sql = OPERATIONAL_ADD_ONLY.read_text(encoding='utf-8')
    operational_statements = split_ddl(operational_sql)
    operational_tables, operational_indexes, operational_fks, operational_order = sql_objects(operational_sql)
    if set(operational_tables) != OPERATIONAL_TABLES or operational_order != prior_order[-len(PLANNING_TABLES)-len(OPERATIONAL_TABLES):-len(PLANNING_TABLES)]:
        raise ValueError('Operational migration does not contain exactly the expected 20 tables')
    if any(operational_tables[name] != tables[name] for name in OPERATIONAL_TABLES):
        raise ValueError('Operational migration definitions differ from authoritative MySQL schema')
    if not operational_indexes <= indexes or not operational_fks <= foreign_keys:
        raise ValueError('Operational migration indexes or foreign keys disagree with schema')
    if len(operational_statements) != 20 or any(not TABLE_PATTERN.match(sql) for sql in operational_statements):
        raise ValueError('Operational patch must consist of 20 CREATE TABLE IF NOT EXISTS statements only')
    if any(forbidden.search(sql) for sql in operational_statements):
        raise ValueError('Operational patch cannot contain destructive DDL or data writes')
    if any('ENGINE=InnoDB' not in sql or 'DEFAULT CHARSET=utf8mb4' not in sql for sql in operational_statements):
        raise ValueError('Operational patch tables require InnoDB and utf8mb4')
    # Optional operational planning/review tables are a sixth, separate migration.
    planning_sql = PLANNING_ADD_ONLY.read_text(encoding='utf-8')
    planning_statements = split_ddl(planning_sql)
    planning_tables, planning_indexes, planning_fks, planning_order = sql_objects(planning_sql)
    if set(planning_tables) != PLANNING_TABLES or planning_order != prior_order[-len(PLANNING_TABLES):]:
        raise ValueError('Planning migration does not contain exactly the expected 20 new tables in order')
    if any(planning_tables[name] != tables[name] for name in PLANNING_TABLES):
        raise ValueError('Planning migration definitions differ from canonical schema')
    if not planning_indexes <= indexes or not planning_fks <= foreign_keys:
        raise ValueError('Planning migration contains inconsistent indexes or FK relationships')
    if len(planning_statements) != 20 or any(not TABLE_PATTERN.match(stmt) for stmt in planning_statements):
        raise ValueError('Planning migration must contain only 20 CREATE TABLE IF NOT EXISTS statements')
    if any(forbidden.search(stmt) for stmt in planning_statements):
        raise ValueError('Planning migration must not change existing data or database objects')
    if any('ENGINE=InnoDB' not in stmt or 'DEFAULT CHARSET=utf8mb4' not in stmt for stmt in planning_statements):
        raise ValueError('Planning migration requires InnoDB and utf8mb4')
    # New controls/reconciliation foundation is a separately reviewed, add-only migration.
    control_sql = CONTROL_ADD_ONLY.read_text(encoding='utf-8')
    control_statements = split_ddl(control_sql)
    control_tables, control_indexes, control_fks, control_order = sql_objects(control_sql)
    if len(control_statements) != 20 or set(control_tables) != CONTROL_TABLES or control_order != ordered[control_start:control_start+len(CONTROL_TABLES)]:
        raise ValueError('Control extension must define exactly the last 20 canonical tables')
    if any(control_tables[name] != tables[name] for name in CONTROL_TABLES):
        raise ValueError('Control migration differs from authoritative backend schema')
    if not control_indexes <= indexes or not control_fks <= foreign_keys:
        raise ValueError('Control extension indexes / FKs differ from canonical definitions')
    if any(not TABLE_PATTERN.match(stmt) for stmt in control_statements):
        raise ValueError('Control extension requires CREATE TABLE IF NOT EXISTS statements only')
    if any(forbidden.search(stmt) or re.search(r'\bON DELETE\s+CASCADE\b', stmt, re.I)
           for stmt in control_statements):
        raise ValueError('Control extension must not rewrite data or cascade-delete records')
    if any('ENGINE=InnoDB' not in stmt or 'DEFAULT CHARSET=utf8mb4' not in stmt
           for stmt in control_statements):
        raise ValueError('Control extension requires InnoDB and utf8mb4')
    if re.search(r'\b(fingerprint_template|iris_template|bank_account_number|password_hash|api_secret)\b',
                 control_sql, re.I):
        raise ValueError('Control extension must not introduce raw biometric templates or credentials')
    # Asset register and inspection tables are a separate, additive migration.
    asset_sql = ASSET_ADD_ONLY.read_text(encoding='utf-8')
    asset_statements = split_ddl(asset_sql)
    asset_tables, asset_indexes, asset_fks, asset_order = sql_objects(asset_sql)
    if asset_order != ordered[control_start+len(CONTROL_TABLES):control_start+len(CONTROL_TABLES)+2] or set(asset_tables) != {'asset_profiles', 'asset_inspections'}:
        raise ValueError('Asset migration must contain exactly the final two canonical tables')
    if any(asset_tables[name] != tables[name] for name in asset_order):
        raise ValueError('Asset migration differs from authoritative schema')
    if not asset_indexes <= indexes or not asset_fks <= foreign_keys:
        raise ValueError('Asset migration indexes or FKs disagree with authoritative schema')
    if len(asset_statements) != 2 or any(not TABLE_PATTERN.match(stmt) or forbidden.search(stmt)
                                         for stmt in asset_statements):
        raise ValueError('Asset migration must be two additive CREATE TABLE statements only')
    # HR data-quality imports are always add-only and store metadata/settings, never workbook bytes.
    quality_sql = QUALITY_IMPORT_ADD_ONLY.read_text(encoding='utf-8')
    quality_statements = split_ddl(quality_sql)
    quality_tables, quality_indexes, quality_fks, _ = sql_objects(quality_sql)
    if len(quality_statements) != 3 or set(quality_tables) != {
        'hr_data_quality_import_settings', 'hr_data_quality_import_history'
    }:
        raise ValueError('HR quality import migration must define exactly two tables and one index')
    if any(quality_tables[name] != tables[name] for name in quality_tables):
        raise ValueError('HR quality import migration differs from canonical schema')
    if not quality_indexes <= indexes or not quality_fks <= foreign_keys:
        raise ValueError('HR quality import index and foreign keys disagree with schema')
    if any(forbidden.search(statement) for statement in quality_statements):
        raise ValueError('HR quality import migration may not alter or delete existing data')
    if any(re.search(r'\bON DELETE\s+CASCADE\b', statement,re.I) for statement in quality_statements):
        raise ValueError('Quality import history must not cascade-delete employee records')
    # Release 18: 20 schema-only operational evidence tables. Existing table order
    # and definitions must remain unchanged; only a contiguous new suffix is allowed.
    evidence_sql = EVIDENCE_ADD_ONLY.read_text(encoding='utf-8')
    evidence_statements = split_ddl(evidence_sql)
    evidence_tables, evidence_indexes, evidence_fks, evidence_order = sql_objects(evidence_sql)
    if len(evidence_statements) != 20 or set(evidence_tables) != EVIDENCE_TABLES:
        raise ValueError('Operational evidence upgrade must declare exactly 20 tables')
    if evidence_order != ordered[-24:-4]:
        raise ValueError('Operational evidence tables must be the final canonical schema declarations')
    if any(evidence_tables[name] != tables[name] for name in evidence_order):
        raise ValueError('Operational evidence upgrade differs from canonical schema')
    if not evidence_indexes <= indexes or not evidence_fks <= foreign_keys:
        raise ValueError('Operational evidence indexes / foreign keys disagree with canonical schema')
    if any(not TABLE_PATTERN.match(stmt) or forbidden.search(stmt) or
           'ENGINE=InnoDB' not in stmt or 'DEFAULT CHARSET=utf8mb4' not in stmt or
           re.search(r'\bON DELETE\s+CASCADE\b', stmt, re.I)
           for stmt in evidence_statements):
        raise ValueError('Operational evidence migration must be safe, add-only MySQL tables')
    if re.search(r'\b(fingerprint_template|iris_template|bank_account_number|password_hash|api_secret)\b',
                 evidence_sql, re.I):
        raise ValueError('Operational evidence schema must not store biometric secrets or credentials')
    # Release 19: four user-facing expense workflow tables with exact, safe DDL parity.
    expenses_sql = EXPENSES_ADD_ONLY.read_text(encoding='utf-8')
    exp_statements = split_ddl(expenses_sql)
    exp_tables, exp_indexes, exp_fks, exp_order = sql_objects(expenses_sql)
    if len(exp_statements) != 4 or exp_order != list(EXPENSE_TABLES) or ordered[-4:] != exp_order:
        raise ValueError('Expense workflow migration must contain four trailing add-only tables (with inline indexes)')
    if any(exp_tables[name] != tables[name] for name in EXPENSE_TABLES):
        raise ValueError('Expense migration differs from the canonical schema')
    if not exp_indexes <= indexes or not exp_fks <= foreign_keys:
        raise ValueError('Expense migration indexes or foreign keys do not match')
    if any(forbidden.search(statement) or re.search(r'\bON DELETE\s+CASCADE\b', statement, re.I) for statement in exp_statements):
        raise ValueError('Expense migration must not overwrite/delete HR data')
    if any('ENGINE=InnoDB' not in exp_tables[name] for name in EXPENSE_TABLES):
        raise ValueError('Expense workflow tables must use InnoDB')
    with INVENTORY.open(newline='', encoding='utf-8-sig') as f:
        rows = list(csv.DictReader(f))
    by_name = {row['Table']: row for row in rows}
    if len(rows) != len(required) or set(by_name) != set(required):
        raise ValueError('Database inventory does not contain every required table exactly once')
    for name, columns in required.items():
        row = by_name[name]
        if set(c.strip() for c in row['Required columns'].split(',')) != columns:
            raise ValueError(f'Inventory columns do not match table {name}')
        if int(row['Column count']) != len(columns):
            raise ValueError(f'Inventory count does not match table {name}')
    visited = set()
    for name in ordered:
        if any(table == name and parent != name and parent not in visited
               for table, _, parent, _ in foreign_keys):
            raise ValueError(f'Table {name} declares an FK to a table created later in the fresh installer')
        visited.add(name)
    for table, col, parent, parent_col in foreign_keys:
        if col not in required[table] or parent not in required or parent_col not in required[parent]:
            raise ValueError(f'Invalid foreign-key relationship {table}.{col} to {parent}.{parent_col}')
    for table, _ in indexes:
        if table not in required:
            raise ValueError(f'Invalid named index for missing table {table}')
    print(f'PASS: {len(tables)} tables, {sum(map(len, required.values()))} columns, '
          f'{len(indexes)} named indexes and {len(foreign_keys)} foreign-key relationships')
    print('PASS: fresh-install DDL, backend schema, manual schema, inventory and all additive migrations agree')
    print('PASS: no seeded candidate/payroll/employee records in fresh-install SQL')
    return required, indexes, foreign_keys


def check_live(expected_database: str, required, indexes, relations):
    from mysql_backend import raw_mysql_connection
    connection = raw_mysql_connection()
    try:
        database, existing_tables, existing_columns = database_inventory(connection)
        if database.casefold() != expected_database.casefold():
            raise ValueError(f'Connected to {database!r}; expected {expected_database!r}; refusing to audit wrong database')
        missing_tables, missing_columns = compare(required, existing_tables, existing_columns)
        with connection.cursor() as cursor:
            cursor.execute('''SELECT TABLE_NAME AS object_name, INDEX_NAME AS index_name
                 FROM information_schema.statistics WHERE table_schema = DATABASE()''')
            existing_indexes = {(str(field(row, 'object_name')).lower(), str(field(row, 'index_name')).lower())
                                for row in cursor.fetchall()}
            cursor.execute('''SELECT TABLE_NAME AS object_name, COLUMN_NAME AS column_name,
                     REFERENCED_TABLE_NAME AS referenced_table, REFERENCED_COLUMN_NAME AS referenced_column
                FROM information_schema.key_column_usage
                WHERE table_schema = DATABASE() AND REFERENCED_TABLE_NAME IS NOT NULL''')
            existing_fks = {(str(field(row, 'object_name')).lower(), str(field(row, 'column_name')).lower(),
                             str(field(row, 'referenced_table')).lower(),
                             str(field(row, 'referenced_column')).lower()) for row in cursor.fetchall()}
        absent_indexes = sorted(indexes - existing_indexes)
        absent_fks = sorted(relations - existing_fks)
        print(f'Live database: {database}; tables found: {len(existing_tables)}')
        for label, values in [('MISSING TABLES', missing_tables),
                              ('MISSING COLUMNS', [f'{t}.{c}' for t,c in missing_columns]),
                              ('MISSING NAMED INDEXES', [f'{t}.{idx}' for t,idx in absent_indexes]),
                              ('MISSING FOREIGN KEYS', [f'{t}.{c} -> {parent}.{parent_col}' for t,c,parent,parent_col in absent_fks])]:
            if values:
                print(f'{label} ({len(values)}): ' + ', '.join(values[:25]) + (' …' if len(values) > 25 else ''))
        if any((missing_tables, missing_columns, absent_indexes, absent_fks)):
            print('FAIL: MySQL schema is incomplete. Back up and review an additive migration; never reset volumes.')
            return 2
        print('PASS: live MySQL includes every expected table, column, named index and FK relationship')
        return 0
    finally:
        connection.close()


def main(argv=None):
    parser = argparse.ArgumentParser(description='Check every SASS HRM MySQL schema module (no writes)')
    parser.add_argument('--live', action='store_true', help='Also query information_schema in the running MySQL database')
    parser.add_argument('--file-only', action='store_true', help='Validate only the bundled schema files')
    parser.add_argument('--expected-database', default=os.getenv('MYSQL_DATABASE', 'sass_hrm'),
                        help='Expected selected MySQL database name (safety guard)')
    args = parser.parse_args(argv)
    if args.file_only and args.live:
        parser.error('--file-only and --live cannot be used together')
    try:
        required, indexes, relations = check_file_package()
        if args.live:
            return check_live(args.expected_database, required, indexes, relations)
        return 0
    except Exception as exc:
        # Never print connection strings, personal records or passwords.
        if isinstance(exc, ValueError):
            print('FAIL:', str(exc))
        else:
            print('FAIL:', type(exc).__name__, '(see local service logs; do not share credentials)')
        return 3


if __name__ == '__main__':
    sys.exit(main())

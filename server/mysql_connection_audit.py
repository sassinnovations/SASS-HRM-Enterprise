"""Read-only, authenticated-safe MySQL schema and table-access audit.

No inserts, DDL, or application records are read. A table-access probe executes
SELECT 1 ... LIMIT 0, checking the DB user's actual SELECT privileges and
that the declared tables can be opened without exposing HR information.
Schema-only expansion tables are NOT claimed to have implemented API workflows.
"""
from __future__ import annotations

from pathlib import Path

from schema_audit import field, get_required_schema
from mysql_feature_schema_integrity import (
    sql_objects, SCHEMA, EXTENSION_TABLES, WORKFLOW_TABLES,
    OPERATIONAL_TABLES, PLANNING_TABLES, CONTROL_TABLES, EVIDENCE_TABLES, OPERATIONS_21_TABLES,
    WORKSPACE_MIGRATION_TABLES, WORKSPACE_SETTINGS_TABLES, WORKSPACE_VIEW_TABLES,
)

FOUNDATION_ONLY = (
    set(EXTENSION_TABLES) | set(WORKFLOW_TABLES) |
    set(OPERATIONAL_TABLES) | set(PLANNING_TABLES) | set(CONTROL_TABLES) | set(EVIDENCE_TABLES) | set(OPERATIONS_21_TABLES)
) - {'recruitment_match_runs','recruitment_match_results',
     'recruitment_match_review_notes','candidate_shortlist_decisions'}
CORE_MODULES = {
    'employees': ('employees', 'employee_skills', 'departments'),
    'attendance_and_leave': ('attendance', 'leave_requests', 'attendance_capture_events'),
    'payroll': ('salary_packages', 'pay_runs_v2', 'pay_items_v2'),
    'candidate_search': ('candidate_profiles', 'candidate_import_batches'),
    'recruitment': ('jobs', 'hiring_stage_settings', 'recruitment_job_descriptions', 'jd_import_batches'),
    'documents': ('document_vault',),
    'workspace_manual_controls': WORKSPACE_MIGRATION_TABLES + WORKSPACE_SETTINGS_TABLES + WORKSPACE_VIEW_TABLES,
    'settings_and_security': ('organization_preferences', 'audit_events', 'hr_data_quality_import_settings', 'hr_data_quality_import_history'),
}


def inspect_mysql_connection(raw, expected_database: str, probe_tables: bool = False) -> dict:
    """Query only MySQL INFORMATION_SCHEMA and optional zero-row table opens.

    A mismatched database name is an error, not a green status for the wrong
    tenant/schema. Never calls install_schema or executes any DML/DDL.
    """
    required = get_required_schema()
    _, expected_indexes, expected_fks, _ = sql_objects(SCHEMA.read_text(encoding='utf-8'))
    if FOUNDATION_ONLY - set(required):
        raise RuntimeError('Foundation inventory refers to a missing schema table')

    with raw.cursor() as cur:
        cur.execute('SELECT DATABASE() AS database_name')
        result = cur.fetchone()
        database = str(field(result, 'database_name') or '') if result else ''
        if not database or database.casefold() != expected_database.casefold():
            raise ValueError('Connected MySQL database does not match the expected SASS HRM database')

        cur.execute('''SELECT TABLE_NAME AS object_name FROM information_schema.tables
            WHERE table_schema=DATABASE() AND table_type='BASE TABLE' ''')
        present = {str(field(row, 'object_name')).lower() for row in cur.fetchall()}
        cur.execute('''SELECT TABLE_NAME AS object_name, COLUMN_NAME AS column_name
            FROM information_schema.columns WHERE table_schema=DATABASE()''')
        cols = {(str(field(row, 'object_name')).lower(), str(field(row, 'column_name')).lower())
                for row in cur.fetchall()}
        cur.execute('''SELECT TABLE_NAME AS object_name, INDEX_NAME AS index_name
            FROM information_schema.statistics WHERE table_schema=DATABASE()''')
        indexes = {(str(field(row, 'object_name')).lower(), str(field(row, 'index_name')).lower())
                   for row in cur.fetchall()}
        cur.execute('''SELECT TABLE_NAME AS object_name, COLUMN_NAME AS column_name,
            REFERENCED_TABLE_NAME AS referenced_table,
            REFERENCED_COLUMN_NAME AS referenced_column
            FROM information_schema.key_column_usage
            WHERE table_schema=DATABASE() AND REFERENCED_TABLE_NAME IS NOT NULL''')
        refs = {(str(field(row, 'object_name')).lower(), str(field(row, 'column_name')).lower(),
                 str(field(row, 'referenced_table')).lower(),
                 str(field(row, 'referenced_column')).lower()) for row in cur.fetchall()}

        missing_tables = sorted(set(required) - present)
        missing_columns = sorted(f'{table}.{column}' for table, names in required.items()
                                 if table in present for column in names
                                 if (table, column) not in cols)
        missing_indexes = sorted(f'{table}.{index}' for table, index in expected_indexes - indexes)
        missing_foreign_keys = sorted(f'{table}.{column} -> {parent}.{ref}'
                                      for table, column, parent, ref in expected_fks - refs)
        access_failures = []
        accessible = None
        if probe_tables:
            accessible = 0
            for table in sorted(set(required) & present):
                try:
                    # Name is from the bundled SQL schema, never user input.
                    cur.execute(f'SELECT 1 FROM `{table}` LIMIT 0')
                    accessible += 1
                except Exception:
                    # Never expose driver exception text: it may include server details.
                    access_failures.append(table)
        migration_version = None
        if 'schema_migrations' in present:
            try:
                cur.execute('SELECT MAX(version) AS schema_version FROM schema_migrations')
                version = cur.fetchone()
                migration_version = field(version, 'schema_version') if version else None
            except Exception:
                # A malformed history table is a schema problem, not permission to repair.
                access_failures.append('schema_migrations')

    is_complete = not (missing_tables or missing_columns or missing_indexes or
                       missing_foreign_keys or access_failures)
    return {
        'engine': 'mysql',
        'database_reachable': True,
        'database_name_matches': True,
        'schema_version': migration_version,
        'table_count': len(present),
        'expected_table_count': len(required),
        'schema_complete': is_complete,
        'missing_tables': missing_tables,
        'missing_columns': missing_columns,
        'missing_indexes': missing_indexes,
        'missing_foreign_keys': missing_foreign_keys,
        'table_access_probed': probe_tables,
        'table_access_passed': accessible,
        'table_access_failures': sorted(set(access_failures)),
        'schema_only_table_count': len(FOUNDATION_ONLY),
        'schema_only_tables': sorted(FOUNDATION_ONLY),
        'pre_expansion_table_count': len(required) - len(FOUNDATION_ONLY),
        'modules': {name: all(table in present for table in tables)
                    for name, tables in CORE_MODULES.items()},
        'tables': sorted(present),
    }

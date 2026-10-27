"""Read-only administrator schema status; tolerant of MySQL metadata key casing."""
from fastapi import Depends
from main import app, db, DB_ENGINE, require_hr
from schema_audit import field


@app.get('/api/admin/database/status')
def database_status(user=Depends(require_hr)):
    with db() as connection:
        if DB_ENGINE == 'mysql':
            table_rows = connection.execute('''SELECT TABLE_NAME AS object_name
                FROM information_schema.tables
                WHERE table_schema=DATABASE() AND table_type='BASE TABLE'
                ORDER BY TABLE_NAME''').fetchall()
            tables = [str(field(row, 'object_name')).lower() for row in table_rows]
            version = 0
            if 'schema_migrations' in tables:
                migration = connection.execute('SELECT MAX(version) AS version FROM schema_migrations').fetchone()
                if migration is not None:
                    version = field(migration, 'version') or 0
        else:
            table_rows = connection.execute('''SELECT name FROM sqlite_master
                WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name''').fetchall()
            tables = [str(field(row, 'name')).lower() for row in table_rows]
            version = 'sqlite-development'
        missing_tables, missing_columns, expected_count = [], [], None
        if DB_ENGINE == 'mysql':
            from schema_audit import get_required_schema
            expected = get_required_schema()
            expected_count = len(expected)
            present = set(tables)
            missing_tables = sorted(set(expected) - present)
            column_rows = connection.execute('''SELECT TABLE_NAME AS object_name,
                COLUMN_NAME AS column_name FROM information_schema.columns
                WHERE table_schema=DATABASE()''').fetchall()
            existing_columns = {(str(field(row, 'object_name')).lower(),
                                 str(field(row, 'column_name')).lower()) for row in column_rows}
            missing_columns = sorted(f'{table}.{column}' for table, required_columns in expected.items()
                                     if table in present for column in required_columns
                                     if (table, column) not in existing_columns)
        present = set(tables)
        return {'engine': DB_ENGINE, 'schema_version': version, 'table_count': len(tables),
                'expected_table_count': expected_count,
                'schema_complete': not missing_tables and not missing_columns if DB_ENGINE == 'mysql' else None,
                'missing_tables': missing_tables, 'missing_columns': missing_columns,
                'modules': {'employees': 'employees' in present,
                            'attendance': 'attendance' in present,
                            'leave': 'leave_requests' in present,
                            'payroll': 'pay_runs_v2' in present,
                            'tax_reference': 'salary_packages' in present,
                            'recruitment': 'candidates' in present,
                            'documents': 'document_vault' in present,
                            'auditing': 'audit_events' in present,
                            'account_recovery': 'password_reset_tokens' in present},
                'tables': tables}

"""HR-admin read-only database diagnostics; no automatic MySQL schema changes."""
import os
from fastapi import Depends, HTTPException
from main import app, db, DB_ENGINE, require_hr
from schema_audit import field


@app.get('/api/admin/database/status')
def database_status(probe_tables: bool = False, user=Depends(require_hr)):
    if DB_ENGINE == 'mysql':
        from mysql_backend import raw_mysql_connection
        from mysql_connection_audit import inspect_mysql_connection
        connection = None
        try:
            connection = raw_mysql_connection()  # Bypass mysql_db's schema installer.
            return inspect_mysql_connection(
                connection, (os.getenv('MYSQL_DATABASE') or os.getenv('MYSQLDATABASE') or 'sass_hrm'), probe_tables=probe_tables
            )
        except ValueError as exc:
            raise HTTPException(503, str(exc)) from exc
        except Exception as exc:
            raise HTTPException(503, 'MySQL verification failed. Check connectivity and run the read-only schema checker.') from exc
        finally:
            if connection is not None:
                connection.close()

    # SQLite is allowed only for isolated tests, never deployed production.
    with db() as connection:
        table_rows = connection.execute('''SELECT name FROM sqlite_master
            WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name''').fetchall()
        tables = [str(field(row, 'name')).lower() for row in table_rows]
    return {'engine': DB_ENGINE, 'database_reachable': True, 'schema_version': 'sqlite-development',
            'table_count': len(tables), 'expected_table_count': None,
            'schema_complete': None, 'missing_tables': [], 'missing_columns': [],
            'missing_indexes': [], 'missing_foreign_keys': [],
            'table_access_probed': False, 'table_access_passed': None,
            'table_access_failures': [], 'schema_only_table_count': None,
            'schema_only_tables': [], 'pre_expansion_table_count': None,
            'modules': {'employees': 'employees' in tables,
                        'attendance_and_leave': 'attendance' in tables,
                        'payroll': 'payslips' in tables,
                        'candidate_search': 'candidates' in tables}, 'tables': tables}

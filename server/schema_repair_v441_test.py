"""Regression checks for read-only metadata audit and safe, opt-in MySQL repair."""
from __future__ import annotations

import io
from contextlib import redirect_stdout
from schema_audit import (field, database_inventory, compare, get_required_schema,
                          duplicate_work_email_count, verify_preflight, main)

class FakeCursor:
    def __init__(self, connection):
        self.connection = connection
        self.rows = []
    def __enter__(self):
        return self
    def __exit__(self, *_):
        return False
    def execute(self, statement):
        # Deliberately use UPPERCASE dictionary keys from information_schema.
        statement = statement.lower()
        self.connection.queries.append(statement)
        if 'select database()' in statement:
            self.rows = [{'DATABASE_NAME': self.connection.database}]
        elif 'information_schema.tables' in statement:
            self.rows = [{'OBJECT_NAME': t} for t in self.connection.tables]
        elif 'information_schema.columns' in statement:
            self.rows = [{'OBJECT_NAME': t, 'COLUMN_NAME': col}
                         for t, col in self.connection.columns]
        elif 'duplicate_emails' in statement:
            self.rows = [{'DUPLICATE_GROUPS': self.connection.duplicate_groups}]
        else:
            raise AssertionError(f'Unexpected SQL: {statement}')
    def fetchone(self):
        return self.rows[0]
    def fetchall(self):
        return self.rows

class FakeConnection:
    def __init__(self, tables, columns, duplicate_groups=0, database='sass_hrm'):
        self.tables, self.columns = tables, columns
        self.duplicate_groups, self.database = duplicate_groups, database
        self.queries = []
    def cursor(self):
        return FakeCursor(self)

required = get_required_schema()
assert len(required) == 105
existing = set(required) - {'profile_photos', 'performance_evidence'}
columns = {(t, c) for t in existing for c in required[t]} - {('employees','work_email')}
conn = FakeConnection(existing, columns)
name, tables, found = database_inventory(conn)
assert name == 'sass_hrm'
assert tables == existing
assert found == columns
assert compare(required, tables, found) == (['performance_evidence','profile_photos'], [('employees','work_email')])
assert verify_preflight(conn, required, 'sass_hrm') == (['performance_evidence','profile_photos'], [('employees','work_email')])
assert all(not q.startswith(('insert','update','delete','create','alter','drop','truncate')) for q in conn.queries)
assert duplicate_work_email_count(conn, False) == 0

def fails(c, match):
    try:
        verify_preflight(c, required, 'sass_hrm')
    except ValueError as e:
        assert match in str(e), str(e)
    else:
        raise AssertionError(f'Expected preflight to reject {match}')

fails(FakeConnection(existing, columns, duplicate_groups=1), 'duplicate')
fails(FakeConnection(existing, columns, database='wrong_db'), 'not')
fails(FakeConnection(existing, columns - {('employees','password_hash')}), 'unreviewed')
fails(FakeConnection(existing - {'employees'}, columns), 'employees')
assert field({'TABLE_NAME': 'employees'}, 'table_name') == 'employees'
# --file-only must never require a database connection.
with redirect_stdout(io.StringIO()) as buf:
    result = main(['--file-only'])
assert result == 0 and 'PASS' in buf.getvalue()
print('PASS: uppercase metadata; read-only audit; strict preflight; email uniqueness; source schema coverage')

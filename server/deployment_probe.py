"""Read-only live MySQL readiness probe for the running SASS HRM API.

Checks the shipped table inventory rather than an incomplete hand-picked subset.
Never prints employee personal information and never writes to MySQL.
"""
from __future__ import annotations

import re
from pathlib import Path

from main import DB_ENGINE, db

if DB_ENGINE != 'mysql':
    raise SystemExit('FAIL: active backend is not configured for MySQL')

schema_sql = Path(__file__).with_name('mysql_schema.sql').read_text(encoding='utf-8')
required = set(re.findall(r'CREATE\s+TABLE\s+IF\s+NOT\s+EXISTS\s+`?(\w+)`?', schema_sql, flags=re.I))
if len(required) < 100:
    raise SystemExit(f'FAIL: unexpected bundled MySQL schema: {len(required)} tables')

with db() as conn:
    found = {str(row['table_name']).lower() for row in conn.execute(
        'SELECT TABLE_NAME AS table_name FROM information_schema.tables WHERE table_schema=DATABASE()'
    ).fetchall()}
    missing = {table.lower() for table in required} - found
    if missing:
        raise SystemExit('FAIL: missing MySQL tables: ' + ', '.join(sorted(missing)))
    migration = conn.execute('SELECT MAX(version) AS v FROM schema_migrations').fetchone()['v']
    employees = conn.execute('SELECT COUNT(*) AS n FROM employees').fetchone()['n']
    candidates = conn.execute('SELECT COUNT(*) AS n FROM candidate_profiles').fetchone()['n']
    batches = conn.execute('SELECT COUNT(*) AS n FROM candidate_import_batches').fetchone()['n']
    print(f'PASS: MySQL schema has all {len(required)} required tables; migration marker {migration}.')
    print(f'PASS: read-only counts: {employees} employees, {candidates} candidate profiles, {batches} candidate import batches.')
    if candidates == 0:
        print('PASS: Candidate library is empty. Add candidates or upload your own Excel workbook when ready.')
    print('No database records were changed by this probe.')

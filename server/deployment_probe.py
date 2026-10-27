"""Read-only MySQL schema inspection executed in the running backend container."""
from main import DB_ENGINE, db

if DB_ENGINE != 'mysql':
    raise SystemExit('FAIL: active backend is not configured for MySQL')
with db() as conn:
    found = {row['table_name'] for row in conn.execute(
        'SELECT TABLE_NAME AS table_name FROM information_schema.tables WHERE table_schema=DATABASE()'
    ).fetchall()}
    required = {
        'employees', 'schema_migrations', 'attendance', 'leave_requests',
        'pay_runs_v2', 'pay_items_v2', 'salary_packages', 'developer_grants',
        'asset_lifecycle_events', 'employee_preferences', 'document_review_events',
        'career_plans', 'service_requests', 'benefit_verification_events',
    }
    missing = required - found
    if missing:
        raise SystemExit('FAIL: missing MySQL tables: ' + ', '.join(sorted(missing)))
    employees = conn.execute('SELECT COUNT(*) AS n FROM employees').fetchone()['n']
    version = conn.execute('SELECT MAX(version) AS v FROM schema_migrations').fetchone()['v']
    print(f'PASS MySQL schema: {len(found)} tables; migration marker {version}; active employee rows {employees}')
    print('No test records were written by this probe.')

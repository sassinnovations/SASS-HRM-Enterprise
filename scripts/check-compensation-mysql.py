"""Read-only live MySQL schema check: never creates or mutates records."""
from pathlib import Path
import os,sys
from dotenv import load_dotenv
root=Path(__file__).resolve().parents[1]
load_dotenv(root/'server'/'.env')
sys.path.insert(0,str(root/'server'))
if os.getenv('DB_ENGINE','').strip().lower()!='mysql':
    raise SystemExit('FAIL: DB_ENGINE is not mysql; this check requires the real MySQL backend')
from mysql_backend import raw_mysql_connection
expected={'expense_review_events','benefit_verification_events','salary_packages','pay_runs_v2',
          'leave_requests','leave_entitlements','timesheet_entries','shifts','shift_assignments',
          'attendance','attendance_corrections','benefit_enrollments','expenses','compensation_workflow_settings'}
connection=raw_mysql_connection()
try:
    with connection.cursor() as cur:
        cur.execute('SELECT TABLE_NAME AS table_name FROM information_schema.tables WHERE table_schema=DATABASE()')
        existing={r['table_name'] for r in cur.fetchall()}
        missing=expected-existing
        if missing:raise SystemExit('FAIL: Missing compensation tables: '+', '.join(sorted(missing))+'. Start the upgraded backend to install them.')
        cur.execute('SELECT version FROM schema_migrations WHERE version=3')
        if not cur.fetchone():raise SystemExit('FAIL: Migration version 3 not recorded. Restart the upgraded backend.')
        for table in sorted(expected):
            cur.execute(f'SELECT count(*) AS total FROM {table}')
            result=cur.fetchone()
            print(f'OK {table}: readable ({result["total"]} rows)')
        print('PASS: Live MySQL compensation schema and migration. This does not verify every workflow or compliance.')
finally:
    connection.close()

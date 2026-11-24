"""Read-only MySQL checks for v1.7 Talent Operations. No data creation or credentials printed."""
from pathlib import Path
import os
import sys
from dotenv import load_dotenv
ROOT=Path(__file__).resolve().parents[1]
load_dotenv(ROOT/'server'/'.env')
sys.path.insert(0,str(ROOT/'server'))
if os.getenv('DB_ENGINE','').lower()!='mysql':
    raise SystemExit('FAIL: DB_ENGINE is not mysql. Run SETUP_SASS_HRM.bat first.')
from mysql_backend import raw_mysql_connection
expected={'candidate_activity','onboarding_templates','ticket_assignments','offboarding_clearance','task_comments','service_messages'}
conn=raw_mysql_connection()
try:
    with conn.cursor() as cur:
        cur.execute('SELECT TABLE_NAME AS table_name FROM information_schema.tables WHERE table_schema=DATABASE()')
        actual={r['table_name'] for r in cur.fetchall()}
        missing=expected-actual
        if missing:raise SystemExit('FAIL: Missing Talent tables: '+', '.join(sorted(missing))+'. Start the backend to apply schema changes.')
        cur.execute('SELECT version,description FROM schema_migrations WHERE version=2')
        migration=cur.fetchone()
        if not migration:raise SystemExit('FAIL: Talent schema migration not recorded. Restart the backend.')
        for table in sorted(expected):
            cur.execute(f'SELECT COUNT(*) AS n FROM {table}')
            count=cur.fetchone()['n']
            print(f'PASS {table}: {count} records')
        print('PASS: MySQL Talent Operations schema, migration and readable tables. This is not a live workflow or security certification.')
finally:
    conn.close()

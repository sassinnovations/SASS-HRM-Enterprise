"""Read-only MySQL schema verification. No employee records are modified."""
import os,sys
from pathlib import Path
from dotenv import load_dotenv
root=Path(__file__).resolve().parents[1]
load_dotenv(root/'server'/'.env')
sys.path.insert(0,str(root/'server'))
if os.getenv('DB_ENGINE','').lower().strip()!='mysql':
    raise SystemExit('FAIL: SASS HRM is NOT connected to MySQL; DB_ENGINE must equal mysql.')
from mysql_backend import raw_mysql_connection
required={'asset_lifecycle_events','document_review_events','employee_preferences'}
conn=raw_mysql_connection()
try:
    with conn.cursor() as cur:
        cur.execute('SELECT TABLE_NAME AS table_name FROM information_schema.tables WHERE table_schema=DATABASE()')
        found={r['table_name'] for r in cur.fetchall()}
        missing=required-found
        if missing:raise SystemExit('FAIL missing tables: '+', '.join(sorted(missing))+'; start v2.0 backend to apply schema.')
        cur.execute('SELECT version FROM schema_migrations WHERE version=5')
        if not cur.fetchone():raise SystemExit('FAIL missing schema migration 5')
        for table in sorted(required):
            cur.execute(f'SELECT COUNT(*) AS n FROM {table}')
            print('PASS '+table+' readable; rows='+str(cur.fetchone()['n']))
        print('PASS v2.0 Employee Services MySQL tables. This does not certify security or full browser functionality.')
finally:
    conn.close()

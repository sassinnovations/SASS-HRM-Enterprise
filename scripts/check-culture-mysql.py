"""Read-only schema check for v1.9. Does not migrate or alter employee data."""
import os,sys
from pathlib import Path
from dotenv import load_dotenv
root=Path(__file__).resolve().parents[1]
load_dotenv(root/'server'/'.env')
sys.path.insert(0,str(root/'server'))
if os.getenv('DB_ENGINE','').lower().strip()!='mysql':
    raise SystemExit('FAIL: DB_ENGINE must be mysql; you may still be using SQLite.')
from mysql_backend import raw_mysql_connection
names={'goal_progress_history','training_verifications','training_verification_events',
       'recognition_reactions','culture_case_status_history',
       'career_plans','employee_voice_cases','discipline_cases','surveys'}
conn=raw_mysql_connection()
try:
    with conn.cursor() as cur:
        cur.execute('SELECT TABLE_NAME AS table_name FROM information_schema.tables WHERE table_schema=DATABASE()')
        existing={r['table_name'] for r in cur.fetchall()}
        missing=names-existing
        if missing:
            raise SystemExit('FAIL missing Culture tables: '+', '.join(sorted(missing))+'. Start updated backend to apply schema.')
        cur.execute('SELECT version FROM schema_migrations WHERE version=4')
        if not cur.fetchone():raise SystemExit('FAIL migration 4 missing. Start upgraded backend first.')
        for name in sorted(names):
            cur.execute(f'SELECT COUNT(*) AS n FROM {name}')
            print(f'PASS {name}: readable ({cur.fetchone()["n"]} rows)')
        print('PASS: Culture v1.9 schema readable with MySQL. This is NOT proof of browser or compliance readiness.')
finally:
    conn.close()

"""Persisted admin-only schema checks; no application records are inspected.

On MySQL, the scanner accesses INFORMATION_SCHEMA and executes zero-row
SELECTs only. Saving findings is a separate, explicit admin-initiated action.
"""
from __future__ import annotations
import csv
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from fastapi import Depends, Query
from main import app, db, require_hr, audit, DB_ENGINE

SQLITE_SCHEMA = """
CREATE TABLE IF NOT EXISTS database_verification_runs (
 id INTEGER PRIMARY KEY, run_status TEXT NOT NULL, expected_tables INTEGER NOT NULL DEFAULT 0,
 present_tables INTEGER NOT NULL DEFAULT 0, missing_tables INTEGER NOT NULL DEFAULT 0,
 missing_columns INTEGER NOT NULL DEFAULT 0, missing_indexes INTEGER NOT NULL DEFAULT 0,
 missing_foreign_keys INTEGER NOT NULL DEFAULT 0, access_failures INTEGER NOT NULL DEFAULT 0,
 requested_by INTEGER NOT NULL REFERENCES employees(id), checked_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS database_verification_findings (
 id INTEGER PRIMARY KEY, run_id INTEGER NOT NULL REFERENCES database_verification_runs(id),
 finding_type TEXT NOT NULL, object_name TEXT NOT NULL, checked_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS database_module_checks (
 id INTEGER PRIMARY KEY, run_id INTEGER NOT NULL REFERENCES database_verification_runs(id),
 module_name TEXT NOT NULL, required_count INTEGER NOT NULL DEFAULT 0,
 present_count INTEGER NOT NULL DEFAULT 0, missing_names TEXT NOT NULL DEFAULT '',
 UNIQUE (run_id,module_name));
"""

@app.on_event('startup')
def init_database_verification_tables():
    if DB_ENGINE == 'sqlite':
        with db() as connection:
            connection.executescript(SQLITE_SCHEMA)


def feature_table_groups() -> dict[str,list[str]]:
    """Every required table must appear in exactly one maintained module."""
    source=Path(__file__).resolve().parent.parent/'database'/'ALL_MYSQL_TABLES.csv'
    groups: dict[str,list[str]] = defaultdict(list)
    with source.open(encoding='utf-8-sig',newline='') as handle:
        for row in csv.DictReader(handle):
            groups[row['Module / responsibility']].append(row['Table'])
    return dict(sorted(groups.items()))


def project_coverage(status: dict) -> list[dict]:
    from schema_audit import get_required_schema
    required=get_required_schema()
    groups=feature_table_groups()
    if set(t for names in groups.values() for t in names) != set(required):
        raise RuntimeError('Database feature inventory does not cover the MySQL schema')
    present=set(status.get('tables',[]))
    live=status.get('engine')=='mysql'
    result=[]
    for label,names in groups.items():
        missing=sorted(t for t in names if t not in present) if live else []
        result.append({'module':label,'required_count':len(names),
                       'present_count':len(names)-len(missing) if live else None,
                       'missing_tables':missing,
                       'state':('complete' if not missing else 'missing_tables') if live else 'not_live_verified'})
    return result


def obtain_status(user,probe_tables=True):
    from mysql_schema_status import database_status
    return database_status(probe_tables=probe_tables,user=user)


@app.get('/api/admin/database/feature-coverage')
def database_feature_coverage(user=Depends(require_hr)):
    status=obtain_status(user,probe_tables=False)
    return {'engine':status['engine'],'schema_complete':status.get('schema_complete'),
            'expected_table_count':status.get('expected_table_count'),
            'modules':project_coverage(status),
            'note':'Table presence and accessibility do not certify an operational screen or workflow.'}


@app.get('/api/admin/database/verification-runs')
def database_verification_history(limit:int=Query(15,ge=1,le=50),user=Depends(require_hr)):
    with db() as connection:
        runs=[dict(r) for r in connection.execute('''SELECT id,run_status,expected_tables,present_tables,
          missing_tables,missing_columns,missing_indexes,missing_foreign_keys,access_failures,
          requested_by,checked_at FROM database_verification_runs ORDER BY id DESC LIMIT ?''',
          (limit,)).fetchall()]
        for entry in runs:
            entry['modules']=[dict(x) for x in connection.execute('''SELECT module_name,required_count,
              present_count,missing_names FROM database_module_checks WHERE run_id=? ORDER BY module_name''',
              (entry['id'],)).fetchall()]
            entry['findings']=[dict(x) for x in connection.execute('''SELECT finding_type,object_name
              FROM database_verification_findings WHERE run_id=? ORDER BY id LIMIT 50''',
              (entry['id'],)).fetchall()]
    return runs


@app.post('/api/admin/database/verification-runs', status_code=201)
def save_database_verification(user=Depends(require_hr)):
    status=obtain_status(user)  # read-only scan before any writable connection
    coverage=project_coverage(status)
    live=status['engine']=='mysql'
    result_status=('Passed' if status.get('schema_complete') else 'NeedsReview') if live else 'NotVerified'
    keys=('missing_tables','missing_columns','missing_indexes','missing_foreign_keys','table_access_failures')
    checked=datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S.%f')
    with db() as conn:
        cur=conn.execute('''INSERT INTO database_verification_runs
            (run_status,expected_tables,present_tables,missing_tables,missing_columns,
            missing_indexes,missing_foreign_keys,access_failures,requested_by,checked_at)
            VALUES (?,?,?,?,?,?,?,?,?,?)''',
            (result_status,int(status.get('expected_table_count') or 0),
             int(status.get('table_count') or 0),*(len(status.get(k,[])) for k in keys),user['id'],checked))
        run_id=cur.lastrowid
        for item in coverage:
            conn.execute('''INSERT INTO database_module_checks
                (run_id,module_name,required_count,present_count,missing_names) VALUES (?,?,?,?,?)''',
                (run_id,item['module'],item['required_count'],item['present_count'] or 0,
                 ','.join(item['missing_tables'])[:2048]))
        # Strictly schema identifiers; never driver errors, HR records, or credentials.
        for key in keys:
            for value in status.get(key,[])[:2500]:
                conn.execute('''INSERT INTO database_verification_findings
                    (run_id,finding_type,object_name,checked_at) VALUES (?,?,?,?)''',
                    (run_id,key,str(value)[:191],checked))
        audit(conn,user['id'],'database.verification.saved',f'database-run:{run_id}',
              f'{result_status}; expected={status.get("expected_table_count")}')
    return {'id':run_id,'run_status':result_status,'schema_complete':status.get('schema_complete'),
            'expected_tables':status.get('expected_table_count'), 'present_tables':status.get('table_count'),
            'module_count':len(coverage),
            'note':'Database structure check only, not business workflow certification.'}

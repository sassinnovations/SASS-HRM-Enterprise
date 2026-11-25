#!/usr/bin/env python3
"""Read-only SASS HRM HTTP 500 diagnostics. Never prints secrets or employee data.

Usage:
  python scripts/diagnose-http-500.py --url https://YOUR-BACKEND.example
  python scripts/diagnose-http-500.py --database

The --database check uses configured local/server environment variables. It opens
MySQL directly and executes SELECT 1 and zero-row table selects, never migrations.
"""
import argparse
import json
import os
import sys
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parent.parent
SERVER = ROOT / 'server'
CORE_TABLES = ('employees', 'attendance', 'candidate_profiles', 'audit_events')


def check_url(base_url: str) -> int:
    url = base_url.rstrip('/')
    if not url.startswith(('https://', 'http://')):
        print('FAIL: --url must begin with https:// or http://')
        return 2
    bad = 0
    for route in ('/api/live', '/api/health', '/api/ready'):
        status, kind, body = None, '', b''
        try:
            with urlopen(Request(url+route, headers={'Accept':'application/json', 'User-Agent':'SASS-HRM-read-only-healthcheck'}),timeout=12) as res:
                status = res.status
                kind = res.headers.get('Content-Type','')
                body = res.read(16384)
        except HTTPError as e:
            status = e.code
            kind = e.headers.get('Content-Type','')
            body = e.read(16384)
        except (URLError, TimeoutError, OSError) as e:
            print(f'FAIL {route}: connection failed ({type(e).__name__}); check DNS, deployment and HTTPS')
            bad += 1
            continue
        try:
            value = json.loads(body)
            is_hrm_json = isinstance(value,dict) and value.get('status') in ('ok','ready','alive')
        except (ValueError, TypeError):
            is_hrm_json = False
        if status == 200 and is_hrm_json:
            print(f'PASS {route}: HTTP 200, expected SASS HRM JSON')
        elif status == 200:
            print(f'FAIL {route}: HTTP 200 but NOT SASS HRM JSON; check frontend rewrite/proxy or backend URL')
            bad += 1
        else:
            print(f'FAIL {route}: HTTP {status}; check backend logs (no private error body printed)')
            bad += 1
    if bad:
        print('\nIf /api/live passes but /api/health fails: the backend runs but MySQL is unreachable.')
        print('If /api/live fails: confirm your backend deployment/start command and URL.')
        print('If all return HTML: VITE_API_URL points to frontend rather than backend.')
    return 2 if bad else 0


def check_database() -> int:
    sys.path.insert(0,str(SERVER))
    try:
        from dotenv import load_dotenv
        load_dotenv(SERVER/'.env')
    except ImportError:
        print('INFO: python-dotenv is unavailable; using environment variables as provided')
    engine = os.getenv('DB_ENGINE','mysql').strip().lower()
    if engine != 'mysql':
        print('FAIL: configured DB_ENGINE is not mysql; production must use mysql')
        return 2
    secret = os.getenv('JWT_SECRET','')
    if len(secret)<40 or secret.startswith(('REPLACE_', 'LOCAL_DEMO', 'CHANGE_ME', 'GENERATED_BY_SETUP')):
        print('FAIL: JWT_SECRET is missing or a placeholder; configure a unique secret >= 40 characters')
        return 2
    from mysql_backend import raw_mysql_connection
    conn = None
    try:
        conn = raw_mysql_connection()
        with conn.cursor() as c:
            c.execute('SELECT 1')
            c.fetchone()
            print('PASS: MySQL connection and SELECT 1')
            for name in CORE_TABLES:
                c.execute(f'SELECT 1 FROM `{name}` LIMIT 0')
                print(f'PASS: required table {name} is accessible (zero rows read)')
    except Exception as e:
        kind=type(e).__name__
        print(f'FAIL: MySQL readiness ({kind}). Check hostname, port, app user credentials, grants and schema.')
        print('Note: do not share environment files or raw database error messages containing secrets.')
        return 2
    finally:
        if conn is not None:
            conn.close()
    return 0


def main():
    p=argparse.ArgumentParser(description=__doc__,formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--url',help='Public backend root URL, not frontend URL')
    p.add_argument('--database', action='store_true',help='Read-only local/host MySQL connectivity check')
    args=p.parse_args()
    if not args.url and not args.database:
        p.print_help()
        return 2
    results=[]
    if args.url:results.append(check_url(args.url))
    if args.database:results.append(check_database())
    return max(results)

if __name__=='__main__':
    sys.exit(main())

"""Refuse mixed Docker/.env credentials or an unsafe production-looking configuration.

Only configuration shape is printed; secret values are never logged.
"""
from __future__ import annotations
import os
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

def config(path):
    if not path.is_file():
        raise ValueError(f'Missing {path.relative_to(ROOT)}. Run SETUP_SASS_HRM.bat for a new deployment.')
    values = {}
    for line in path.read_text(encoding='utf-8-sig').splitlines():
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        if '=' not in line:
            raise ValueError(f'Invalid configuration line in {path.name}; expected KEY=VALUE')
        key, val = line.split('=', 1)
        sanitized = val.strip().strip('"').strip("'")
        if '\r' in sanitized or '\n' in sanitized:
            raise ValueError(f'{path.name} contains a carriage-return or multiline value in {key}; rewrite it in LF format.')
        values[key.strip()] = sanitized
    return values

def verify():
    compose = config(ROOT / '.env')
    api = config(ROOT / 'server' / '.env')
    for name in ('MYSQL_DATABASE', 'MYSQL_USER', 'MYSQL_PASSWORD'):
        if not compose.get(name) or compose[name] != api.get(name):
            raise ValueError(f'{name} differs between .env and server/.env. Do not change a populated MySQL volume password casually.')
    if not compose.get('MYSQL_ROOT_PASSWORD'):
        raise ValueError('Missing MYSQL_ROOT_PASSWORD')
    if api.get('DB_ENGINE', '').lower() != 'mysql':
        raise ValueError('DB_ENGINE must be mysql for the real SASS HRM stack')
    if api.get('MYSQL_PORT') != '3307' or api.get('MYSQL_HOST') not in ('127.0.0.1', 'localhost'):
        raise ValueError('server/.env should use 127.0.0.1:3307 for the Windows backend; Docker overrides it internally')
    jwt = api.get('JWT_SECRET', '')
    if len(jwt) < 40 or jwt.startswith(('REPLACE_', 'LOCAL_DEMO', 'CHANGE_ME', 'GENERATED_')):
        raise ValueError('JWT_SECRET must be randomly generated (40+ chars)')
    if any(v.startswith('GENERATED_') for v in compose.values()):
        raise ValueError('Default placeholder database credentials are not allowed')
    for key in ('MYSQL_PASSWORD', 'MYSQL_ROOT_PASSWORD'):
        if re.search(r'[\s#]', compose[key]):
            raise ValueError(f'{key} must not contain whitespace or # in the current Docker environment format')
    if api.get('APP_ENV', '').lower() == 'production':
        raise ValueError('This local HTTP Docker Compose setup must not be declared production; configure HTTPS, SSO/MFA and audited secrets first')
    print('PASS: MySQL configuration, shared credentials and JWT setup are consistent (secret values hidden).')

if __name__ == '__main__':
    try:
        verify()
    except ValueError as exc:
        print('FAIL:', exc)
        raise SystemExit(1)

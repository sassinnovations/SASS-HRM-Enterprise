"""Check server/.env shape. Secret values are never logged."""
from __future__ import annotations
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
    api = config(ROOT / 'server' / '.env')
    compose_path = ROOT / '.env'
    if compose_path.is_file():
        compose = config(compose_path)
        for name in ('MYSQL_DATABASE', 'MYSQL_USER', 'MYSQL_PASSWORD'):
            if compose.get(name) and compose[name] != api.get(name):
                raise ValueError(f'{name} differs between .env and server/.env.')
        if any(v.startswith('GENERATED_') for v in compose.values()):
            raise ValueError('Default placeholder database credentials are not allowed')
    if api.get('DB_ENGINE', '').lower() != 'mysql':
        raise ValueError('DB_ENGINE must be mysql for the real SASS HRM stack')
    for name in ('MYSQL_HOST', 'MYSQL_PORT', 'MYSQL_DATABASE', 'MYSQL_USER', 'MYSQL_PASSWORD'):
        if not api.get(name) or api[name].startswith('GENERATED_'):
            raise ValueError(f'server/.env {name} must be set to the MySQL service, not a placeholder')
    if not api['MYSQL_PORT'].isdigit():
        raise ValueError('MYSQL_PORT must be a number, usually 3306')
    jwt = api.get('JWT_SECRET', '')
    if len(jwt) < 40 or jwt.startswith(('REPLACE_', 'LOCAL_DEMO', 'CHANGE_ME', 'GENERATED_')):
        raise ValueError('JWT_SECRET must be randomly generated (40+ chars)')
    if re.search(r'[\s#]', api['MYSQL_PASSWORD']):
        raise ValueError('MYSQL_PASSWORD must not contain whitespace or #')
    print('PASS: MySQL configuration and JWT setup are consistent (secret values hidden).')

if __name__ == '__main__':
    try:
        verify()
    except ValueError as exc:
        print('FAIL:', exc)
        raise SystemExit(1)

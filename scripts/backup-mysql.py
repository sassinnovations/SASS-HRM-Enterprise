"""MySQL dump using the server/.env connection. No Docker and no data changes."""
from __future__ import annotations
import datetime as dt
import os
import shutil
import subprocess
import sys
from pathlib import Path

root = Path(__file__).resolve().parent.parent
env_path = root / 'server' / '.env'
if not env_path.is_file():
    sys.exit('Missing server/.env. Set MYSQL_HOST, MYSQL_PORT, MYSQL_USER, MYSQL_PASSWORD and MYSQL_DATABASE.')

def read_env(path: Path) -> dict[str, str]:
    values = {}
    for line in path.read_text(encoding='utf-8-sig').splitlines():
        line = line.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue
        key, value = line.split('=', 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values

settings = read_env(env_path)
required = ('MYSQL_HOST', 'MYSQL_PORT', 'MYSQL_USER', 'MYSQL_PASSWORD', 'MYSQL_DATABASE')
missing = [name for name in required if not settings.get(name)]
if missing:
    sys.exit('server/.env is missing: ' + ', '.join(missing))

mysqldump = shutil.which('mysqldump')
if not mysqldump:
    candidate = Path(r'C:\Program Files\MySQL\MySQL Server 8.0\bin\mysqldump.exe')
    if candidate.is_file():
        mysqldump = str(candidate)
if not mysqldump:
    sys.exit('mysqldump was not found. Install the MySQL client and add it to PATH.')

folder = root / 'backups'
folder.mkdir(exist_ok=True)
output = folder / ('sass_hrm_' + dt.datetime.now(dt.timezone.utc).strftime('%Y%m%d_%H%M%S') + '.sql')
command = [
    mysqldump,
    '-h', settings['MYSQL_HOST'],
    '-P', settings['MYSQL_PORT'],
    '-u', settings['MYSQL_USER'],
    '--single-transaction',
    '--routines',
    '--triggers',
    settings['MYSQL_DATABASE'],
]
env = os.environ.copy()
env['MYSQL_PWD'] = settings['MYSQL_PASSWORD']
try:
    with output.open('wb') as dump:
        result = subprocess.run(command, cwd=root, stdout=dump, stderr=subprocess.PIPE, timeout=240, env=env)
    if result.returncode:
        output.unlink(missing_ok=True)
        print('Backup failed. Confirm MySQL is reachable. Details:', result.stderr.decode('utf-8', 'replace')[:900])
        sys.exit(1)
    if output.stat().st_size < 100:
        output.unlink(missing_ok=True)
        sys.exit('Backup output unexpectedly empty; backup discarded.')
    print('Backup created:', output, f'({output.stat().st_size} bytes)')
    print('Keep backups encrypted and outside the web directory. Validate restores in a separate MySQL instance.')
except (OSError, subprocess.TimeoutExpired) as exc:
    output.unlink(missing_ok=True)
    sys.exit(f'Backup failed: {exc}')

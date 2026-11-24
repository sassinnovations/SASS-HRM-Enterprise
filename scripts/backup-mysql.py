"""Binary-safe MySQL backup from the existing Docker volume; no data is modified."""
from __future__ import annotations
import datetime as dt
import os
from pathlib import Path
import subprocess
import sys

root = Path(__file__).resolve().parent.parent
folder = root / 'backups'
folder.mkdir(exist_ok=True)
name = 'sass_hrm_' + dt.datetime.now(dt.timezone.utc).strftime('%Y%m%d_%H%M%S') + '.sql'
output = folder / name
compose = root / 'docker-compose.mysql.yml'
command = [
    'docker', 'compose', '-f', str(compose), 'exec', '-T', 'mysql',
    'sh', '-c',
    'MYSQL_PWD="$MYSQL_ROOT_PASSWORD" exec mysqldump --single-transaction '
    '--routines --triggers -uroot "$MYSQL_DATABASE"',
]
try:
    with output.open('wb') as dump:
        result = subprocess.run(command, cwd=root, stdout=dump, stderr=subprocess.PIPE, timeout=240)
    if result.returncode:
        output.unlink(missing_ok=True)
        print('Backup failed. Confirm Docker/MySQL is healthy. Details:', result.stderr.decode('utf-8', 'replace')[:900])
        sys.exit(1)
    if output.stat().st_size < 100:
        output.unlink(missing_ok=True)
        sys.exit('Backup output unexpectedly empty; backup discarded.')
    print('Backup created:', output, f'({output.stat().st_size} bytes)')
    print('Keep backups encrypted and outside the web directory. Validate restores in a separate MySQL instance.')
except (OSError, subprocess.TimeoutExpired) as exc:
    output.unlink(missing_ok=True)
    sys.exit(f'Backup failed: {exc}')

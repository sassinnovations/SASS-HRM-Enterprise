"""Dependency-light full-stack config and safety regressions; does not start Docker."""
from __future__ import annotations
import importlib.util
import os
from pathlib import Path
import tempfile

root = Path(__file__).resolve().parent.parent
text = (root / 'docker-compose.full.yml').read_text(encoding='utf-8')
try:
    import yaml
except ImportError:
    yaml = None
if yaml:
    # Both the legacy database-only launcher and the full stack must be valid YAML.
    old=yaml.safe_load((root/'docker-compose.mysql.yml').read_text(encoding='utf-8'))
    assert old['name']=='sass_hrm_real' and set(old['services'])=={'mysql'}
    assert old['services']['mysql']['healthcheck']['test'][0]=='CMD-SHELL'
    doc=yaml.safe_load(text)
    assert doc['name']=='sass_hrm_real'
    services=doc['services']
    assert set(services)=={'mysql','api','web'}
    assert services['api']['depends_on']['mysql']['condition']=='service_healthy'
    assert services['web']['depends_on']['api']['condition']=='service_healthy'
    assert services['mysql']['volumes'][0]=='sass_hrm_mysql_data:/var/lib/mysql'
    for service, port in [('mysql','3307'),('api','8000'),('web','5173')]:
        assert str(services[service]['ports'][0]).startswith('127.0.0.1:' + port + ':'), service
        assert services[service]['healthcheck']['test']
else:
    assert all(s in text for s in ('mysql:', 'api:', 'web:', '127.0.0.1:5173:80'))

for name in ('docker/backend.Dockerfile','docker/frontend.Dockerfile','docker/nginx.conf',
             'scripts/start-docker-full.ps1','scripts/verify-docker-full.ps1',
             'scripts/backup-mysql.py','server/deployment_probe.py'):
    assert (root/name).is_file(), f'Missing {name}'
nginx=(root/'docker/nginx.conf').read_text()
assert 'proxy_pass http://api:8000;' in nginx and 'try_files $uri $uri/ /index.html' in nginx
ignore=(root/'.dockerignore').read_text()
for token in ('**/.env', '**/*.db', '**/node_modules', 'backups'):
    assert token in ignore, f'Unprotected build input {token}'
assert 'docker compose down -v' not in (root/'scripts/start-docker-full.ps1').read_text()
assert "'exec', '-T'" in (root/'scripts/backup-mysql.py').read_text()

spec=importlib.util.spec_from_file_location('runtime_configuration',root/'scripts/check-runtime-config.py')
mod=importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
with tempfile.TemporaryDirectory() as tmp:
    mod.ROOT=Path(tmp)
    (mod.ROOT/'server').mkdir()
    (mod.ROOT/'.env').write_text('MYSQL_DATABASE=sass_hrm\nMYSQL_USER=sass_hrm_app\nMYSQL_PASSWORD=testing_random\nMYSQL_ROOT_PASSWORD=testing_root\n')
    (mod.ROOT/'server/.env').write_text('APP_ENV=development\nDB_ENGINE=mysql\nMYSQL_HOST=127.0.0.1\nMYSQL_PORT=3307\nMYSQL_DATABASE=sass_hrm\nMYSQL_USER=sass_hrm_app\nMYSQL_PASSWORD=testing_random\nJWT_SECRET=' + 'f'*64 + '\n')
    mod.verify()
    (mod.ROOT/'server/.env').write_text((mod.ROOT/'server/.env').read_text().replace('MYSQL_PASSWORD=testing_random','MYSQL_PASSWORD=different'))
    try:
        mod.verify()
    except ValueError as e:
        assert 'MYSQL_PASSWORD differs' in str(e)
    else:
        raise AssertionError('Mismatched database password was not rejected')

print('PASS Docker Compose services, isolation, healthchecks, nginx routing, build exclusions, and credential mismatch rejection')

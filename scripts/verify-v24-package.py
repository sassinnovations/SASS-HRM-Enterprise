"""Distribution regression: no environment secrets/dependency blobs; deterministic frontend install."""
from pathlib import Path
import argparse
import json

parser=argparse.ArgumentParser(description="Audit either a distributable ZIP source tree or a configured local workspace")
parser.add_argument("--workspace", action="store_true", help="Allow local .env files and installed dependencies; ensure they are excluded from shipping")
args=parser.parse_args()

ROOT=Path(__file__).resolve().parent.parent
if args.workspace:
    dockerignore=(ROOT/'.dockerignore').read_text(encoding='utf-8')
    gitignore=(ROOT/'.gitignore').read_text(encoding='utf-8')
    for name in ('.env','**/.env','**/node_modules','**/dist'):
        assert name in dockerignore, f'Docker ignore missing {name}'
    for name in ('.env','node_modules','dist'):
        assert name in gitignore, f'Git ignore missing {name}'
else:
    assert not (ROOT/'.env').exists(), 'A local root .env would leak into a shared release'
    assert not (ROOT/'server/.env').exists(), 'A local server/.env would leak into a shared release'
assert (ROOT/'.env.example').is_file()
assert (ROOT/'server/.env.example').is_file()
if not args.workspace:
    for excluded in ('web/node_modules','web/dist','web/tsconfig.tsbuildinfo'):
        assert not (ROOT/excluded).exists(), f'Shipped platform-specific artifact: {excluded}'
config=json.loads((ROOT/'web/package.json').read_text())
lock=json.loads((ROOT/'web/package-lock.json').read_text())
assert config['version']==lock['version']==lock['packages']['']['version']=='4.5.0'
assert 'npm ci' in (ROOT/'docker/frontend.Dockerfile').read_text()
assert 'npm ci' in (ROOT/'scripts/start-frontend.ps1').read_text()
assert (ROOT/'REPAIR_FRONTEND.bat').is_file()
assert (ROOT/'server/exports_v24_test.py').is_file()
assert (ROOT/'docs/V2_4_SECURITY_EXPORT_RELEASE.md').is_file()
assert (ROOT/'server/accounts_v25.py').is_file()
assert (ROOT/'server/accounts_v25_test.py').is_file()
assert (ROOT/'docs/V2_5_ACCOUNT_ADMINISTRATION.md').is_file()
print('PASS: workspace ignores protect local secrets and build assets' if args.workspace else 'PASS: distributable tree contains no credentials, dependency caches or compiled output')

"""Static v2.8.1 release integrity check; never connects to live database."""
from pathlib import Path
import argparse
import json

parser=argparse.ArgumentParser()
parser.add_argument("--workspace",action="store_true",help="Check installed project without rejecting private local files")
args=parser.parse_args()

root = Path(__file__).resolve().parent.parent
web = (root/'web/src/TalentTools.tsx').read_text(encoding='utf8')
backend = (root/'server/talent_ops.py').read_text(encoding='utf8')
app = (root/'web/src/App.tsx').read_text(encoding='utf8')
pkg = json.loads((root/'web/package.json').read_text(encoding='utf8'))
lock = json.loads((root/'web/package-lock.json').read_text(encoding='utf8'))
assert pkg['version']==lock['version']=='4.5.0'
assert 'export function TalentTools' in web
assert 'Authorization:`Bearer ${token}`' in web
assert 'VITE_API_URL' in web
assert 'role="dialog"' in web and 'aria-modal="true"' in web
assert 'Search by employee' in web and 'Clear filters' in web
assert "'/talent/onboarding/templates?include_archived=true'" in web
for endpoint in ["'/api/talent/candidates/{candidate_id}/details'",
                 "'/api/talent/onboarding/templates/{template_id}'",
                 "'/api/talent/tasks/{task_id}/details'"]:
    assert endpoint in backend, endpoint
assert 'require_manager' in backend and 'require_hr' in backend
assert "version='4.5.0'" in (root/'server/main.py').read_text(encoding='utf8')
assert 'talent_v281_test.py' in [p.name for p in (root/'server').glob('*_test.py')]
if not args.workspace:
    for excluded in ('web/node_modules','web/dist','web/tsconfig.tsbuildinfo','server/.env','.env'):
        assert not (root/excluded).exists(), f'Shipped local secret or generated artifact: {excluded}'
print('PASS talent compatibility checks on v4.5.0 package: authorization, dialogs, search/filter, edit permissions, version and clean distribution')

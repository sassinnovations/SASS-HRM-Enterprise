"""Dependency-free static audit for demo-reference theme and feature preservation.
Run from project root: python scripts/verify-design-parity.py
This is NOT a substitute for browser rendering or interactive click testing.
"""
import json, re
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
SRC=ROOT/'web/src'
app=(SRC/'App.tsx').read_text(encoding='utf-8')
style=(SRC/'style.css').read_text(encoding='utf-8')
ops=(SRC/'OperationsExtra.tsx').read_text(encoding='utf-8')
payroll=(SRC/'PayrollExtra.tsx').read_text(encoding='utf-8')
menu_body=app.split('const menus:MenuItem[]=[',1)[1].split('];',1)[0]
menu_ids=set(re.findall(r"\{key:'([^']+)'",menu_body))
# All forty v1.0 menu destinations, including the archive and secure vault.
reference='dashboard employees orgchart skills privateprofile workmode compliance accounts attendance corrections shifts timesheets leave recruitment onboarding payrollengine taxcalculator payroll performance training helpdesk expenses assets documents vault offboarding organization policies benefits recognition surveys interviews tasks approvals calendar reports audit readiness assistant settings'.split()
missing=set(reference)-menu_ids
assert not missing,f'Missing demo module(s): {sorted(missing)}'
assert len(menu_ids)>=41, f'Expected demo modules plus developer console, found {len(menu_ids)}'
assert 'developer' in menu_ids and "user?.developer_access" in app
for feature in reference+['developer']:
    assert re.search(r"page\s*===\s*['\"]"+re.escape(feature)+r"['\"]",app),f'No page screen for {feature}'
groups=app.split('const menuGroups:',1)[1].split('];',1)[0]
grouped=set(re.findall(r"'([^']+)'",','.join(re.findall(r'keys:\[([^\]]+)\]',groups))))
assert menu_ids-grouped == {'assistant','settings'},f'Navigation group coverage: {menu_ids-grouped}'
assert 'PayrollWorkbench' in app and 'TaxCalculator' in app
assert 'AttendanceCorrections' in app and 'DocumentVault' in app and 'ReadinessCenter' in app
assert 'DeveloperConsole' in app and '/developer/status' in app
assert '<AI user={person}/>' in app
assert 'admin@demo.sass.local' not in app and 'Demo@12345' not in app
assert 'demo' not in (ROOT/'server/create_admin.py').read_text().lower() or 'demo' not in (ROOT/'server/create_admin.py').read_text().split('def main')[0].lower()
expected={
  '--sass-primary: #5a5fe9;', '--sass-page: #f7f9fd;', '--sass-surface: #ffffff;',
  '--sass-primary-soft: #eef0ff;', '--sass-text: #24304a;',
  'linear-gradient(155deg,#242a72,#4a47ab 55%,#6660bc)',
  'linear-gradient(107deg,#f1f2ff 0%,#f8f7ff 67%,#eeedff 100%)'
}
for value in expected: assert value in style, f'Demo theme missing {value}'
assert 'SASS HRM 1.4 | DEMO-REFERENCE DESIGN SYSTEM' in style
assert '#092653' not in style and '#144781' not in style, 'Navy v1.3 overrides survived'
for name in ['.ops-button','.pay-primary','.nav-list button.active','.login-intro','.welcome-banner','.section-card','.sidebar','.content']:
    assert name in style, f'Unstyled module group: {name}'
# This is a design/feature validator, not a release-version allowlist.
# A version bump must not mask actual regressions or block unrelated test suites.
package_file = ROOT / 'web/package.json'
assert package_file.is_file(), 'Missing frontend package.json'
package = json.loads(package_file.read_text(encoding='utf-8'))
assert package.get('name') == 'sass-hrm-enterprise-web', 'Unexpected frontend package name'
release_version = str(package.get('version', ''))
assert re.fullmatch(r'\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?', release_version), (
    f'Invalid frontend semantic version: {release_version!r}'
)
assert package.get('scripts', {}).get('build'), 'Frontend build script is missing' 
assert 'companysetup' in menu_ids and 'AdminSetupCenter' in app
assert (SRC/'AdminSetup.tsx').exists() and (SRC/'admin-setup.css').exists()
for module in ['career','voice','discipline','requestdesk']:
    assert f"key:'{module}'" in app and f"'{module}'" in groups
assert "CultureModule" in app and (SRC/'CultureSuite.tsx').exists()
culture_source=(SRC/'CultureSuite.tsx').read_text()
for term in ['/career/plans','/voice/cases','/discipline/cases','/request-desk/requests']:
    assert term in culture_source, f'Missing connected culture screen: {term}'
print(f'PASS design parity for SASS HRM v{release_version}: demo-reference palette + unified backgrounds; {len(reference)} original demo screens + Developer Console present; all navigation routes grouped.')
print('PASS 1.5: Career Development, Employee Voice, Discipline and Request Desk screens/routes included.')
print('NOTE: static checks do not prove browser visuals or networked MySQL integration.')

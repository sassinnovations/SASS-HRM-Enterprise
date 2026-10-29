"""Static checks for version-aware MySQL onboarding, no external services required."""
from pathlib import Path
import json
ROOT=Path(__file__).resolve().parent.parent
package=json.loads((ROOT/'web/package.json').read_text())
version=package['version']
assert version=='4.5.0'
backend=(ROOT/'server/main.py').read_text()
setup=(ROOT/'server/organization_setup.py').read_text()
admin=(ROOT/'web/src/AdminSetup.tsx').read_text()
verification=(ROOT/'scripts/diagnose-connection.ps1').read_text()
railway=(ROOT/'railway.toml').read_text()
assert 'healthcheckPath = "/api/health"' in railway
assert 'uvicorn main:app' in railway
assert "version='4.5.0'" in backend and "'version':app.version" in backend
assert "'backend_version':app.version" in setup
assert "const FRONTEND_RELEASE='4.5.0'" in admin
assert "summary?.database_engine==='mysql'" in admin and "summary?.backend_version===FRONTEND_RELEASE" in admin
assert "disabled={busy||!safeConnection}" in admin
assert "disabled={busy||!safeConnection||!validation?.can_import}" in admin
assert "-ne '4.5.0'" in verification
assert (ROOT/'DIAGNOSE_CONNECTION.bat').exists()
assert (ROOT/'scripts/diagnose-connection.ps1').exists()
assert "required=True" in (ROOT/'server/create_admin.py').read_text()
print('PASS: v2.5 frontend/backend version parity, MySQL-only setup safety, stale API smoke checks and diagnostic script')

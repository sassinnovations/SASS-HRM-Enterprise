"""Static checks for version-aware MySQL onboarding, no external services required."""
from pathlib import Path
import json
ROOT=Path(__file__).resolve().parent.parent
package=json.loads((ROOT/'web/package.json').read_text())
version=package['version']
assert version=='4.8.0'
backend=(ROOT/'server/main.py').read_text()
setup=(ROOT/'server/organization_setup.py').read_text()
admin=(ROOT/'web/src/AdminSetup.tsx').read_text()
importer=(ROOT/'web/src/DataQualityImporter.tsx').read_text()
verification=(ROOT/'scripts/verify-docker-full.ps1').read_text()
assert "version='4.8.0'" in backend and "'version':app.version" in backend
assert "'backend_version':app.version" in setup
assert "const FRONTEND_RELEASE='4.8.0'" in admin
assert "summary?.database_engine==='mysql'" in admin and "summary?.backend_version===FRONTEND_RELEASE" in admin
assert "disabled={busy||!safeConnection}" in admin
# Employee import now uses the dedicated DataQualityImporter, not the old
# company-profile form. Check the actual preview/commit gates in the new flow.
importer=(ROOT/'web/src/DataQualityImporter.tsx').read_text(encoding='utf-8')
assert '{safeConnection&&<DataQualityImporter' in admin
assert "if(!file||!preview?.preview_token||preview.error_count||confirm!=='IMPORT')" in importer
assert "'x-import-preview-token':preview.preview_token" in importer
import_api=(ROOT/'server/data_quality_import.py').read_text(encoding='utf-8')
assert 'async def commit_import(request: Request,user=Depends(require_hr))' in import_api
assert '$expectedVersion=(Get-Content' in verification
assert '$api.version -ne $expectedVersion' in verification
assert (ROOT/'DIAGNOSE_CONNECTION.bat').exists()
assert (ROOT/'scripts/diagnose-connection.ps1').exists()
assert "required=True" in (ROOT/'server/create_admin.py').read_text()
print('PASS: v2.5 frontend/backend version parity, MySQL-only setup safety, stale API smoke checks and diagnostic script')

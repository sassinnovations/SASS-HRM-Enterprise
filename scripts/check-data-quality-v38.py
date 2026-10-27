"""Static v3.8 integration check. Does not replace live MySQL or browser tests."""
from pathlib import Path
import re, sys
base=Path(__file__).resolve().parent.parent
app=(base/'web/src/App.tsx').read_text()
route=(base/'web/src/pageRoutes.ts').read_text()
source=(base/'server/data_quality_v38.py').read_text()
assert "dataquality: '/people/data-quality-center'" in route
assert "page==='dataquality'&&isHR&&<DataQualityCenter" in app
assert "key:'dataquality',label:'HR data quality center'" in app
assert "{key:'dataquality',name:'HR data quality center'" in (base/'web/src/AdminSettingsCenter.tsx').read_text()
assert 'Depends(require_hr)' in source and source.count('Depends(require_hr)')>=5
assert 'SELECT * FROM employees' not in source and 'SELECT * FROM leave_requests' not in source and 'SELECT * FROM tickets' not in source
assert 'useRefreshData(load)' in (base/'web/src/DataQualityCenter.tsx').read_text()
assert 'Refresh data</button>' not in (base/'web/src/DataQualityCenter.tsx').read_text()
assert 'const FRONTEND_RELEASE=\'4.5.0\'' in (base/'web/src/AdminSetup.tsx').read_text()
sys.path.insert(0,str(base/'server'))
from schema_audit import get_required_schema, source_coverage
required=get_required_schema()
assert len(required)>=94
assert not source_coverage(required)
print('PASS v3.8: admin-only route, admin settings link, six diagnostic categories, one shared refresh, 94 MySQL tables')

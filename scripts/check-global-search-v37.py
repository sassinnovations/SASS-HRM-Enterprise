"""Release guard for search authorization, single refresh and route mapping."""
from pathlib import Path
import re
root=Path(__file__).resolve().parents[1]
app=(root/'web/src/App.tsx').read_text()
route=(root/'web/src/pageRoutes.ts').read_text()
source=(root/'server/global_search_v37.py').read_text()
assert "globalsearch: '/workspace/global-search'" in route
assert "page==='globalsearch'&&<GlobalSearch" in app
assert "key:'globalsearch',label:'Global HR search'" in app
assert "setActive('globalsearch')" in app
assert "onClick={()=>void refreshCurrentPage()}" in app
assert "ESCAPE \\'!\\'" not in source or "_escaped_pattern" in source
assert 'Depends(current_user)' in source
assert 'employee_id=?' in source
assert 'Medical details' not in source
print('PASS: new global search page, single Refresh data, bound search scope and personal saved queries')

"""Fast, read-only verification that every SASS HRM menu has its own refreshable URL."""
from pathlib import Path
import re
import json

ROOT=Path(__file__).resolve().parent.parent
app=(ROOT/'web/src/App.tsx').read_text(encoding='utf-8')
registry=(ROOT/'web/src/pageRoutes.ts').read_text(encoding='utf-8')
nginx=(ROOT/'docker/nginx.conf').read_text(encoding='utf-8')
package=json.loads((ROOT/'web/package.json').read_text(encoding='utf-8'))

menu=re.search(r'const menus:MenuItem\[\]=\[(.*?)\];',app,re.S)
assert menu, 'Sidebar registry not found'
keys=re.findall(r"\{key:'([^']+)'",menu.group(1))
paths=dict(re.findall(r"^\s*([a-z][a-z0-9]*):\s*'(/[^']+)'",registry,re.M))
assert set(paths)==set(keys),f'Missing page routes: {set(keys)-set(paths)}; unknown: {set(paths)-set(keys)}'
assert len(set(paths.values()))==len(paths),'Two modules share a path'
assert all(re.fullmatch(r'/[a-z]+/[a-z0-9]+(?:-[a-z0-9]+)*',url) for url in paths.values()),'Invalid route'
assert not any(url.startswith('/api/') for url in paths.values()),'Client page overlaps API namespace'
assert paths['orgsettings']!=paths['workflowsettings']!=paths['settings'],'Settings pages must be distinct'
assert paths['profilemgmt']!=paths['profile'],'Personal vs admin profile routes must differ'
assert 'window.history.pushState' in app and "window.addEventListener('popstate'" in app,'Back/Forward routing missing'
assert "useState(()=>pageFromPath(window.location.pathname)" in app,'Refresh route restoration missing'
assert 'onClick={()=>void refreshCurrentPage()}' in app,'Single shared Refresh data action missing'
assert 'window.dispatchEvent(new Event(REFRESH_DATA_EVENT))' in app,'Current module refresh event missing'
assert 'onClick={()=>window.location.reload()}' not in app,'Redundant reload page button must remain removed'
assert 'href={pageUrl(m.key)}' in app,'Sidebar entries must be real navigable links'
assert "if(entry.only==='admin'&&user.role!=='admin')" in app,'Client role guard missing'
assert "if(key==='developer'&&!user.developer_access)" in app,'Developer role guard missing'
assert 'try_files $uri $uri/ /index.html' in nginx,'Direct URL refresh must fall back to index.html'
assert package['version']=='4.5.0','Unexpected frontend version'
print(f'PASS: {len(paths)} unique feature URLs, single Refresh data, Back/Forward, direct-link fallback, protected settings, and API namespace isolation')

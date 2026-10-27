"""Static route-to-screen coverage and release checklist for SASS HRM.

This checks all React menu entries and their screen mounts. It intentionally does
NOT claim MySQL, production bundle, or browser interactions were exercised.
"""
from pathlib import Path
import re,csv,sys

ROOT=Path(__file__).resolve().parent.parent
app=(ROOT/'web/src/App.tsx').read_text(encoding='utf-8')
routes=(ROOT/'web/src/pageRoutes.ts').read_text(encoding='utf-8')
nginx=(ROOT/'docker/nginx.conf').read_text(encoding='utf-8')
menu_body=re.search(r'const menus:MenuItem\[\]=\[(.*?)\];',app,re.S)
groups_body=re.search(r'const menuGroups:.*?=\[(.*?)\];',app,re.S)
assert menu_body and groups_body,'Menu or navigation groups not found'
items=[dict(key=m.group(1),label=m.group(2),restriction=m.group(3) or '') for m in re.finditer(r"\{key:'([^']+)',label:'([^']+)',icon:[^,}\n]+(?:,only:'(admin|management)')?\}",menu_body.group(1))]
paths=dict(re.findall(r"^\s*([a-z][a-z0-9]*):\s*'(/[^']+)'",routes,re.M))
assert len(items)==70,(len(items),'expected exactly the 70 modules')
assert set(v['key'] for v in items)==set(paths), 'Menu does not match the route registry'
assert len(set(paths.values()))==len(paths), 'Repeated URLs'
assert all(re.fullmatch(r'/[a-z]+/[a-z0-9]+(?:-[a-z0-9]+)*',url) for url in paths.values()),'Unsafe URL pattern'
assert 'try_files $uri $uri/ /index.html' in nginx, 'Nginx direct-route reload fallback missing'
assert "setRouteError({kind:'forbidden'" in app and "setRouteError({kind:'not-found'" in app, 'Deep-link error screens missing'
assert "page==='__unavailable__'&&routeError" in app, 'Direct-link error view is not rendered'
assert 'window.addEventListener(\'popstate\'' in app and 'window.history.pushState' in app,'Browser history navigation missing'
assert 'href={pageUrl(m.key)}' in app,'Sidebar links must support opening directly'

indirect={
 'performancecycles':('PerformanceSuite.tsx','<PerformanceSuite'),
 'appraisals':('PerformanceSuite.tsx','<PerformanceSuite'),
 'checkins':('PerformanceSuite.tsx','<PerformanceSuite'),
 'growthplans':('PerformanceGrowth.tsx','<PerformanceGrowth'),
 'feedbackrequests':('PerformanceGrowth.tsx','<PerformanceGrowth'),
 'followups':('PerformanceFollowups.tsx','<PerformanceFollowups'),
 'evidence':('PerformanceJournal.tsx','<PerformanceJournal'),
 'goaljournal':('PerformanceJournal.tsx','<PerformanceJournal'),
 'reviewprogress':('PerformanceFollowups.tsx','<PerformanceFollowups'),
 'workcenter':('WorkspaceControl.tsx','<WorkspaceControl'),
 'globalsearch':('GlobalSearch.tsx','<GlobalSearch'),
 'dataquality':('DataQualityCenter.tsx','<DataQualityCenter'),
 'inbox':('WorkspaceControl.tsx','<WorkspaceControl'),
 'workflowsettings':('WorkspaceControl.tsx','<WorkspaceControl'),
 'career':('CultureSuite.tsx','<CultureModule'),
 'voice':('CultureSuite.tsx','<CultureModule'),
 'discipline':('CultureSuite.tsx','<CultureModule'),
 'requestdesk':('CultureSuite.tsx','<CultureModule'),
}
# The extras below are intentional, and not evidence of duplicated pages.
group_matches=re.findall(r"\{title:'([^']+)',keys:\[([^\]]+)\]\}",groups_body.group(1))
groups={}
for group, keys in group_matches:
 for key in re.findall(r"'([^']+)'",keys):
  assert key not in groups, 'Feature appears in two sidebar groups: '+key
  groups[key]=group
assert set(groups)=={item['key'] for item in items}-{'assistant','settings'}, 'Sidebar group coverage mismatch'

rows=[]
for item in items:
 key=item['key']
 if key in indirect:
  module,mount=indirect[key]
  screen=(ROOT/'web/src'/module).read_text(encoding='utf-8')
  assert mount in app, 'Component is not mounted: '+key
  if key in ('followups','reviewprogress'):
   assert '/api/performance-followups' in screen and 'useRefreshData(load)' in screen, 'Performance follow-up API/refresh integration missing'
  elif key in ('growthplans','feedbackrequests'):
   assert '/api/performance-growth' in screen and 'useRefreshData(load)' in screen, 'Performance growth page missing API/refresh integration'
  elif key in ('performancecycles','appraisals','checkins'):
   assert '/api/performance-v2' in screen, 'Performance API integration not found'
  elif key in ('evidence','goaljournal'):
   assert '/performance-journal' in screen and 'useRefreshData(load)' in screen, 'Performance journal missing API/refresh integration'
  elif key=='dataquality':
   assert 'function DataQualityCenter' in screen and '/admin/data-quality/issues' in screen, 'Data quality page missing API integration'
  elif key=='globalsearch':
   assert 'function GlobalSearch' in screen and '/search/records' in screen, 'Global search is not mounted'
  else:
   assert "'"+key+"'" in screen, 'Component does not handle the requested feature: '+key
 else:
  assert "page==='"+key+"'" in app, 'No matching screen for '+key
  module='App.tsx'
 rows.append({'Group':groups.get(key,'AI & Preferences'), 'Feature':item['label'], 'Route':paths[key],
              'Access':('Administrator' if item['restriction']=='admin' else 'Management' if item['restriction']=='management' else 'Authenticated user'),
              'Screen source':'web/src/'+module,'Navigation / screen source check':'Passed',
              'Live UI and workflow check':'Not tested — requires running Docker/browser and real role accounts'})
assert len(rows)==70
if '--csv' in sys.argv:
 target=ROOT/'docs/SASS_HRM_70_PAGE_CHECKLIST.csv'
 target.parent.mkdir(parents=True,exist_ok=True)
 with target.open('w',encoding='utf-8-sig',newline='') as f:
  writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
 print('Saved',target)
print('PASS:',len(rows),'unique URLs and mounted screens, grouped sidebar, restricted-route/404 feedback, nginx direct-link fallback')
print('NOTE: static verification is not an end-to-end production browser/MySQL test')

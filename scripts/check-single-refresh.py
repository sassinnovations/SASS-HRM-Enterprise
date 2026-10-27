"""Dependency-free, read-only audit of unified refresh controls and handlers.

Checks shipped React source and hooks; it does not emulate a live browser or API.
"""
from pathlib import Path
import re
ROOT=Path(__file__).resolve().parent.parent
src=ROOT/'web/src'
app=(src/'App.tsx').read_text(encoding='utf-8')
hook=(src/'useRefreshData.ts').read_text(encoding='utf-8')
assert 'aria-label="Refresh data"' in app,'Top-bar Refresh data button missing'
assert app.count('aria-label="Refresh data"')==1,'Multiple top-bar Refresh data controls'
assert 'onClick={()=>void refreshCurrentPage()}' in app,'Refresh action not wired'
assert 'await refresh();' in app and 'window.dispatchEvent(new Event(REFRESH_DATA_EVENT))' in app,'Global refresh does not update module subscriptions'
assert 'if(selectedTicket)await showTicket(selectedTicket)' in app,'Open helpdesk conversation is not refreshed'
assert "window.addEventListener(REFRESH_DATA_EVENT,onRefresh)" in hook,'Refresh event subscription missing'
assert "window.removeEventListener(REFRESH_DATA_EVENT,onRefresh)" in hook,'Refresh event cleanup missing'
assert "window.location.reload()" not in app,'Redundant page-reload control remains'
controls=[]
for file in src.glob('*.tsx'):
    text=file.read_text(encoding='utf-8')
    for match in re.finditer(r'<(?:button|Button)\b[\s\S]*?</(?:button|Button)>',text):
        value=match.group()
        if re.search(r'\b(?:Refresh|Reload)(?:\s|<|\'|\")',value,re.I):
            controls.append((file.name,match.start(),value[-160:]))
assert len(controls)==2, f'Expected one Refresh data + crash recovery button only; found {controls!r}'
assert {file for file,_,_ in controls}=={'App.tsx','main.tsx'}, f'Unexpected refresh controls: {controls!r}'
assert 'Refresh data</span></button>' in controls[0][2] or any('Refresh data</span></button>' in text for _,_,text in controls)
assert any('Reload app</button>' in value for _,_,value in controls),'Error boundary must retain its crash recovery action'
required={
 'WorkspaceControl.tsx', 'WorkforcePlanning.tsx', 'WorkflowReminders.tsx',
 'TalentTools.tsx', 'CompensationTools.tsx', 'CompensationSettings.tsx',
 'AdminSettingsCenter.tsx', 'AdminSetup.tsx', 'OrganizationSettings.tsx',
 'OperationsExtra.tsx', 'EmployeeServicesV20.tsx', 'ProfileCenter.tsx',
 'SelfServiceHub.tsx', 'PayrollExtra.tsx', 'CultureSuite.tsx',
 'CultureEnhancements.tsx', 'PersonalCalendar.tsx', 'SetupProgress.tsx',
}
missing=[name for name in required if 'useRefreshData(' not in (src/name).read_text(encoding='utf-8')]
assert not missing,f'Pages without local refresh subscriptions: {missing}'
print(f'PASS: one visible Refresh data control; {len(required)} module files subscribe to in-page data refresh; only the error boundary retains crash recovery.')

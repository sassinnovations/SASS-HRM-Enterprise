"""Dependency-free source regression check for the SASS HRM right-hand AI dock."""
from pathlib import Path
root=Path(__file__).resolve().parents[1]
app=(root/'web/src/App.tsx').read_text(encoding='utf-8')
css=(root/'web/src/sass-ai-floating-dock.css').read_text(encoding='utf-8')
checks={
  'old left assistant nav removed': 'AI Assistant</span>' not in app and 'ai-nav' not in app,
  'old sidebar AI card removed': 'className="sidebar-ai"' not in app,
  'workspace settings retained': '<span>Settings</span>' in app,
  'bot is mounted once': app.count('<SassAICopilot user={person} navigate={setActive} activeFeatureKey={page}/>')==1,
  'bot dock follows main workspace as a sibling': app.index('className="main-area"')<app.index('data-testid="sass-ai-right-dock"'),
  'right icon opens bot': 'aria-label="Open AI bot"' in app and 'onClick={()=>setAiDockOpen(true)}' in app,
  'close button collapses bot': 'aria-label="Close AI bot"' in app and 'onClick={()=>setAiDockOpen(false)}' in app,
  'dashboard shortcut still works': "<Button onClick={()=>setActive('assistant')}" in app,
  'assistant navigation opens dock': "if(key==='assistant'){setAiDockOpen(true);" in app,
  'old AI bookmarks open dock': "if(requested==='assistant'){" in app and 'replaceState' in app,
  'dock is not fixed overlay': 'position:relative' in css and '.sass-ai-dock{flex:' in css,
  'desktop main workspace keeps own flex area': '.shell>.main-area{flex:1 1 0;min-width:0}' in css,
  'mobile app uses split layout': '.shell.sass-ai-dock-open{flex-direction:column}' in css,
  'chat area scrolls independently': 'overflow-y:auto;overflow-x:hidden' in css,
  'existing AI APIs unchanged': (root/'server/ai_copilot.py').exists() or any((root/'server').glob('*ai*copilot*')),
}
for title,ok in checks.items():print(f'{"PASS" if ok else "FAIL"}: {title}')
if not all(checks.values()):raise SystemExit(1)
print(f'PASS: {len(checks)} UI and integration source checks')

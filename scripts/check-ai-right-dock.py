"""Dependency-free regression check for the floating, non-modal SASS AI bot.

Kept under the original filename so existing CHECK_AI_RIGHT_DOCK.bat works.
"""
from pathlib import Path
root = Path(__file__).resolve().parents[1]
app = (root / 'web/src/App.tsx').read_text(encoding='utf-8')
widget = (root / 'web/src/FloatingAIBot.tsx').read_text(encoding='utf-8')
css = (root / 'web/src/sass-ai-floating-dock.css').read_text(encoding='utf-8')
ai = (root / 'web/src/SassAICopilot.tsx').read_text(encoding='utf-8')
checks = {
  'left sidebar AI Assistant entry removed': 'AI Assistant</span>' not in app and 'className="sidebar-ai"' not in app,
  'workspace settings navigation retained': '<span>Settings</span>' in app,
  'floating widget rendered once on authenticated app': app.count('<FloatingAIBot open={aiDockOpen}') == 1,
  'assistant mounted exactly once inside widget': widget.count('<SassAICopilot user={user} navigate={navigate} activeFeatureKey={activeFeatureKey}/>') == 1,
  'no old right rail in app': 'sass-ai-dock-rail' not in app,
  'main app layout remains independent of open state': 'return <div className="shell">' in app,
  'right floating icon toggles chat': 'sass-ai-floating-launcher' in widget and 'onOpenChange(!open)' in widget,
  'close/minimize control exists': 'aria-label="Close AI bot"' in widget and 'onOpenChange(false)' in widget,
  'expand and restore controls exist': 'setMaximized(v => !v)' in widget,
  'desktop pointer dragging exists': 'setPointerCapture' in widget and 'onPointerMove={moveDrag}' in widget,
  'keyboard repositioning available': 'onKeyDown={keyboardMove}' in widget,
  'window is not modal': 'aria-modal="false"' in widget,
  'no screen-blocking backdrop introduced': 'sass-ai-overlay' not in css and 'backdrop-filter' not in css,
  'floating fixed launcher and window': '.sass-ai-floating-launcher{' in css and '.sass-ai-floating-window{' in css and css.count('position:fixed') >= 2,
  'window can be resized': 'resize:both' in css,
  'window content independently scrolls': 'overflow:auto;overscroll-behavior:contain' in css,
  'responsive mobile window': '@media (max-width:820px)' in css and 'resize:none' in css,
  'no left or right sidebar layout shift': '.shell.sass-ai-dock-open' not in css and 'flex-basis:clamp(' not in css,
  'dashboard shortcut opens bot': "<Button onClick={()=>setActive('assistant')}" in app,
  'old assistant links still open bot': "if(key==='assistant'){setAiDockOpen(true);" in app,
  'AI conversation and action code unchanged': 'async function planFeature(' in ai and 'const [messages,setMessages]' in ai,
  'existing AI API handlers available': (root / 'server/ai_copilot.py').exists() or any((root / 'server').glob('*ai*copilot*')),
}
for label, passed in checks.items(): print(f'{"PASS" if passed else "FAIL"}: {label}')
if not all(checks.values()): raise SystemExit(1)
print(f'PASS: {len(checks)} floating assistant regression checks')

"""Cross-module reliability guard for the v4.5.0 source bundle."""
from pathlib import Path
import re
root=Path(__file__).resolve().parent.parent
source=root/'web'/'src'
client=(source/'apiTransport.ts').read_text(encoding='utf-8')
app=(source/'App.tsx').read_text(encoding='utf-8')
assert 'DEFAULT_API_TIMEOUT_MS = 25000' in client
assert "HRM_SESSION_EXPIRED" in client and "response.status === 401" in client
assert "authorization === `Bearer ${currentToken}`" in client
assert 'callerSignal?.removeEventListener' in client
assert 'connectionUnavailable' in client
assert 'sass-connectivity-warning' in app
assert 'Your session expired or was revoked' in app
assert 'if(failed.length<entry.length)setLastSync' in app
files=list(source.glob('*.tsx'))
used=0
for file in files:
    text=file.read_text(encoding='utf-8')
    assert not re.search(r'(?<![\w])fetch\s*\(',text), f'Unmanaged fetch in {file.name}'
    if 'hrmFetch(' in text:
        assert "from './apiTransport'" in text, file.name
        used+=1
assert used>=20, f'Expected shared transport across main and module pages, got {used}'
assert app.count('aria-label="Refresh data"') == 1, 'Refresh button duplication detected'
print(f'PASS: {used} frontend modules use shared transport; single Refresh data control, session and outage handling preserved')

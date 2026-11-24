"""Offline SASS HRM — SASS INNOVATIONS ENTERPRISE display-name integrity check."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXPECTED = 'SASS HRM — SASS INNOVATIONS ENTERPRISE'
checks = {
    'web/index.html': [EXPECTED, '<meta name="description"'],
    'web/src/App.tsx': ['SASS INNOVATIONS ENTERPRISE</small>', EXPECTED, 'SASS HRM · SASS INNOVATIONS ENTERPRISE'],
    'web/src/main.tsx': [EXPECTED],
    'server/main.py': [f"FastAPI(title='{EXPECTED} API'", f"'service':'{EXPECTED}'"],
    'server/developer_access.py': [f"'service':'{EXPECTED}'"],
    'server/platform_plus.py': [EXPECTED],
    'server/accounts_v25.py': [EXPECTED],
    'web/src/PayrollExtra.tsx': ['SASS INNOVATIONS ENTERPRISE · PAY STATEMENT'],
    'README.md': [EXPECTED],
}
for file_name, fragments in checks.items():
    contents = (ROOT / file_name).read_text(encoding='utf-8')
    for fragment in fragments:
        assert fragment in contents, (file_name, fragment)
print(f'PASS: {len(checks)} core files use SASS INNOVATIONS ENTERPRISE branding')

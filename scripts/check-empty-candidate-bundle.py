"""Offline check: release contains no bundled personal candidate records or preloaded SQL."""
from pathlib import Path
import re

root=Path(__file__).resolve().parents[1]
assert not list((root/'imports').glob('*.xls*')), 'A candidate Excel workbook is unexpectedly included'
assert not (root/'database'/'06_CANDIDATES_ALL_7435_ROWS_PRELOAD.sql').exists(), 'Old candidate SQL seed must be removed'
assert not (root/'scripts'/'check_candidate_preload.py').exists(), 'Outdated preload test still present'
assert not (root/'imports'/'candidate_role_catalog.json').exists(), 'The 29 legacy role suggestions must be removed'
for path in (root/'database').glob('*.sql'):
    sql=path.read_text(encoding='utf-8')
    if re.search(r'INSERT\s+INTO\s+[`"]?candidates\b',sql,re.I):
        raise SystemExit(f'Candidate insert detected in {path.name}')
print('PASS: source package contains zero preloaded candidate records and zero preloaded job roles.')

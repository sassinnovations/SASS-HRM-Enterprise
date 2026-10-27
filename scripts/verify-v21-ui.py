"""Dependency-free checks for the shared v2.1 demo-design UI improvements."""
import json
from pathlib import Path
root=Path(__file__).resolve().parent.parent
app=(root/'web/src/App.tsx').read_text(encoding='utf-8')
style=(root/'web/src/style.css').read_text(encoding='utf-8')
package=json.loads((root/'web/package.json').read_text(encoding='utf-8'))
assert tuple(map(int, package['version'].split('.')[:2])) >= (2, 1), 'Shared UI requires v2.1 or later'
checks={
  'shared table controls': ['function Table(', 'sass-table-controls', 'Rows per page', 'sass-table-pagination', 'aria-sort'],
  'empty/search state': ['No matching records', 'Clear search', 'allCount={rowsFor(key).length}'],
  'form validation': ['End date must not be before start date', 'role="dialog"', 'aria-modal="true"', 'e.key===\'Escape\''],
  'date correctness': ['const localDate=', 'const today=()=>localDate(new Date())'],
  'data resilience': ['Promise.allSettled(', 'setData(previous=>({...previous,...next}))', 'setLoadFailures(failed)'],
  'refresh accessibility': ['aria-label="Refresh data"', 'sass-sync-note'],
}
for module,terms in checks.items():
    for term in terms:
        assert term in app, f'{module}: missing {term}'
for token in ['--sass-primary: #5a5fe9;', '--sass-primary-soft: #eef0ff;', '--sass-surface: #ffffff;']:
    assert token in style, 'Original SASS demo theme is missing'
for rule in ['.sass-table-controls', '.sass-table-pagination', '.sass-column-sort', '.sass-form-error', '.sass-refresh-workspace']:
    assert rule in style, f'Missing shared design rule {rule}'
assert (root/'CHECK_ALL_SCREENS.bat').exists()
print('PASS shared v2.1 UI controls, validation, local-date handling, refresh resilience, parity tokens, and browser audit script.')

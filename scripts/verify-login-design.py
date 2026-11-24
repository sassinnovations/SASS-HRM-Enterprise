"""Dependency-free regression check for SASS HRM login UI source and responsive CSS.
This does not replace a production browser run against a deployed app.
"""
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
app=(ROOT/'web/src/App.tsx').read_text(encoding='utf-8')
css=(ROOT/'web/src/style.css').read_text(encoding='utf-8')
component=app.split('function Login(',1)[1].split('function DialogBox(',1)[0]
for feature in (
    "'/auth/login'", "'/auth/activate'", "'/auth/password-reset/request'", "'/auth/password-reset/confirm'",
    'login-shell', 'login-panel', 'login-intro', 'login-card', 'login-password-visibility',
    'autoComplete="current-password"', 'autoComplete="username"',
    'aria-expanded={activating}', 'aria-expanded={recovering}', 'role="alert"',
    'Show password', 'Hide password', 'Activate account', 'Save new password'
):
    assert feature in component, f'Missing required login UI/auth capability: {feature}'
for rule in ('.login-panel {','.login-password-visibility {','.login-recovery-heading {',
             '@media (max-width: 900px)', '@media (max-width: 520px)',
             '@media (max-height: 710px) and (min-width: 901px)'):
    assert rule in css, f'Missing responsive login rule: {rule}'
assert 'grid-template-columns: minmax(0, 1fr) minmax(0, 1fr)' in css
assert 'Everything connected.' in component
assert 'role="alert"' in component
print('PASS: SASS HRM login forms, JWT login route, invite/password recovery, accessible controls and desktop/mobile CSS present.')
print('NOTE: this static check cannot confirm live browser/auth/database behavior.')

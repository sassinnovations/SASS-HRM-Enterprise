"""Regression: ESI requires explicit HR handling above the standard wage ceiling."""
import os
import tempfile
from pathlib import Path

os.environ.update(
    SASS_HRM_TESTING='1', DB_ENGINE='sqlite',
    JWT_SECRET='isolated-payroll-esi-review-secret-with-more-than-forty-characters',
)
from fastapi.testclient import TestClient

with tempfile.TemporaryDirectory(prefix='sass-esi-check-') as directory:
    os.environ['DATABASE_PATH'] = str(Path(directory) / 'esi_review.db')
    import main
    with TestClient(main.app) as client:
        with main.db() as c:
            for code, name, email, role in [
                ('HR01', 'ESI Test HR', 'esi-hr@sass.invalid', 'admin'),
                ('EM01', 'ESI Test Employee', 'esi-employee@sass.invalid', 'employee'),
            ]:
                c.execute(
                    '''INSERT INTO employees(code,name,email,role,designation,department,location,join_date,password_hash,account_active)
                       VALUES(?,?,?,?,?,?,?,?,?,1)''',
                    (code, name, email, role, 'Test', 'Operations', 'Remote', '2026-01-01',
                     main.hash_password('SecureESITestPassword!123')),
                )
            employee_id = c.execute('SELECT id FROM employees WHERE code=?', ('EM01',)).fetchone()[0]
        def login(email):
            response = client.post('/api/auth/login', json={'email': email, 'password': 'SecureESITestPassword!123'})
            assert response.status_code == 200, response.text
            return {'Authorization': 'Bearer ' + response.json()['token']}
        hr = login('esi-hr@sass.invalid')
        employee = login('esi-employee@sass.invalid')
        salary = {
            'employee_id': employee_id, 'basic': 20000, 'hra': 3000, 'allowance': 0,
            'pf_enabled': False, 'esi_enabled': True, 'tax_regime': 'new',
        }
        path = f'/api/payroll-v2/salary-packages/{employee_id}'
        blocked = client.put(path, json=salary, headers=hr)
        assert blocked.status_code == 422, blocked.text
        assert 'specialist review' in blocked.json()['detail'], blocked.text
        assert 'contribution period' in blocked.json()['detail'], blocked.text
        assert client.get('/api/payroll-v2/salary-packages', headers=hr).json() == []
        rejected = client.put(path, json={**salary, 'esi_enabled': False}, headers=employee)
        assert rejected.status_code == 403, rejected.text
        pending = client.put(path, json={**salary, 'esi_enabled': False}, headers=hr)
        assert pending.status_code == 200, pending.text
        listed = client.get('/api/payroll-v2/salary-packages', headers=hr)
        assert listed.status_code == 200, listed.text
        assert listed.json()[0]['esi_enabled'] == 0, listed.text
        assert listed.json()[0]['basic'] == 20000, listed.text
        # Standard ceiling is inclusive: specialist eligibility must still be confirmed in practice.
        boundary = client.put(path, json={**salary, 'basic': 18000, 'esi_enabled': True}, headers=hr)
        assert boundary.status_code == 200, boundary.text
        over_ceiling = client.put(path, json={**salary, 'basic': 20000, 'esi_enabled': True}, headers=hr)
        assert over_ceiling.status_code == 422, over_ceiling.text
        assert client.get('/api/payroll-v2/salary-packages', headers=hr).json()[0]['basic'] == 18000
    ui = (Path(__file__).resolve().parent.parent / 'web/src/PayrollExtra.tsx').read_text()
    assert 'Turn ESI off pending assessment (form only)' in ui
    assert 'click Save salary package' in ui
    assert 'esiReviewRequired' in ui
print('ESI review regression passed: permissions, eligibility guard, unsaved form action, and salary persistence.')

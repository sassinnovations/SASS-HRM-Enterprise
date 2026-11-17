"""Safe payroll removal tests (isolated SQLite; no live payroll or employee data)."""
import os
import tempfile
from pathlib import Path

os.environ.update(
    SASS_HRM_TESTING='1', DB_ENGINE='sqlite',
    JWT_SECRET='isolated-payroll-delete-regression-secret-more-than-forty-characters',
)
from fastapi.testclient import TestClient

with tempfile.TemporaryDirectory(prefix='sass-payroll-removal-') as path:
    os.environ['DATABASE_PATH'] = str(Path(path) / 'payroll.db')
    import main
    with TestClient(main.app) as client:
        with main.db() as c:
            for code, name, email, role in [
                ('PADMIN', 'Payroll Administrator', 'payroll-admin@sass.invalid', 'admin'),
                ('PEMP', 'Payroll Employee', 'payroll-employee@sass.invalid', 'employee'),
            ]:
                c.execute('''INSERT INTO employees
                    (code,name,email,role,designation,department,location,join_date,password_hash,account_active)
                    VALUES(?,?,?,?,?,?,?,?,?,1)''',
                    (code, name, email, role, 'Test', 'Finance', 'Test', '2026-01-01',
                     main.hash_password('DeletePayrollTestPassword!123')))
            employee_id = c.execute('SELECT id FROM employees WHERE code=?', ('PEMP',)).fetchone()[0]

        def auth(email):
            res = client.post('/api/auth/login', json={
                'email': email, 'password': 'DeletePayrollTestPassword!123'})
            assert res.status_code == 200, res.text
            return {'Authorization': 'Bearer ' + res.json()['token']}

        admin, employee = auth('payroll-admin@sass.invalid'), auth('payroll-employee@sass.invalid')
        deletion = {'confirm': 'DELETE', 'reason': 'Correcting payroll test data'}
        pkgurl = f'/api/payroll-v2/salary-packages/{employee_id}'
        adjurl = f'/api/payroll-v2/adjustments/{employee_id}/2026-11'
        package = {'employee_id': employee_id, 'basic': 30000, 'hra': 5000,
                   'allowance': 2000, 'esi_enabled': False, 'pf_enabled': False,
                   'tax_regime': 'old', 'tds_mode': 'manual', 'monthly_tds': 1000}
        adjustment = {'employee_id': employee_id, 'month': '2026-11',
                      'bonus': 200, 'reimbursements': 0, 'extra_deductions': 50,
                      'days_worked': 30, 'payable_days': 30}
        assert client.put(pkgurl, headers=admin, json=package).status_code == 200
        assert client.put(adjurl, headers=admin, json=adjustment).status_code == 200
        # Auth, confirmation and orphan protections.
        assert client.request('DELETE', pkgurl, json=deletion).status_code == 401
        assert client.request('DELETE', pkgurl, headers=employee, json=deletion).status_code == 403
        assert client.request('DELETE', pkgurl, headers=admin, json={'confirm': 'WRONG', 'reason': 'Correcting test data'}).status_code == 422
        assert client.request('DELETE', pkgurl, headers=admin, json={'confirm': 'DELETE', 'reason': '   '}).status_code == 422
        assert client.request('DELETE', pkgurl, headers=admin, json=deletion).status_code == 409
        # Snapshot stays until run is explicitly removed.
        run = client.post('/api/payroll-v2/runs', headers=admin, json={'month': '2026-11'})
        assert run.status_code == 201, run.text
        run_id = run.json()['id']
        runurl = f'/api/payroll-v2/runs/{run_id}'
        assert client.request('DELETE', adjurl, headers=employee, json=deletion).status_code == 403
        assert client.request('DELETE', runurl, headers=employee, json=deletion).status_code == 403
        assert client.request('DELETE', runurl, headers=admin, json={'confirm': 'delete', 'reason': 'Correcting test data'}).status_code == 422
        reviewed = client.post(f'{runurl}/transition', headers=admin, json={'action': 'review', 'reviewed': True, 'note':'Verified all payroll figures', 'checklist': {'roster':True,'adjustments':True,'statutory':True}})
        assert reviewed.status_code == 200, reviewed.text
        assert client.request('DELETE', adjurl, headers=admin, json=deletion).status_code == 409
        result = client.request('DELETE', runurl, headers=admin, json=deletion)
        assert result.status_code == 200, result.text
        assert result.json()['removed_items'] == 1
        assert client.get(runurl, headers=admin).status_code == 404
        with main.db() as c:
            assert c.execute('SELECT COUNT(*) FROM pay_items_v2 WHERE run_id=?', (run_id,)).fetchone()[0] == 0
            assert c.execute('SELECT COUNT(*) FROM salary_packages WHERE employee_id=?', (employee_id,)).fetchone()[0] == 1
            assert c.execute('SELECT COUNT(*) FROM pay_adjustments_v2 WHERE employee_id=?', (employee_id,)).fetchone()[0] == 1
        # Both records can be explicitly removed only after the run is gone.
        assert client.request('DELETE', adjurl, headers=admin, json=deletion).status_code == 200
        assert client.request('DELETE', adjurl, headers=admin, json=deletion).status_code == 404
        assert client.request('DELETE', pkgurl, headers=admin, json=deletion).status_code == 200
        assert client.request('DELETE', pkgurl, headers=admin, json=deletion).status_code == 404
        with main.db() as c:
            assert c.execute('SELECT COUNT(*) FROM employees WHERE id=?', (employee_id,)).fetchone()[0] == 1
        # Rebuild and create another run; Published is always protected.
        assert client.put(pkgurl, headers=admin, json=package).status_code == 200
        again = client.post('/api/payroll-v2/runs', headers=admin, json={'month': '2026-11'})
        assert again.status_code == 201, again.text
        again_id = again.json()['id']
        with main.db() as c:
            c.execute("UPDATE pay_runs_v2 SET status='Published' WHERE id=?", (again_id,))
        published_path = f'/api/payroll-v2/runs/{again_id}'
        assert client.request('DELETE', published_path, headers=admin, json=deletion).status_code == 409
        assert client.get(published_path, headers=admin).status_code == 200
        assert client.get('/api/payroll-v2/my-statements', headers=employee).json()
        # Removing a salary package may not modify previously published snapshot values.
        assert client.request('DELETE', pkgurl, headers=admin, json=deletion).status_code == 200
        assert client.get(published_path, headers=admin).json()['items'][0]['gross'] > 0
        assert client.get('/api/payroll-v2/my-statements', headers=employee).json()
        with main.db() as c:
            audit_actions = [r[0] for r in c.execute('SELECT action FROM audit_events WHERE action LIKE ?', ('payroll.%deleted%',)).fetchall()]
            assert {'payroll.salary_package_deleted', 'payroll.adjustment_deleted', 'payroll.unpublished_run_deleted'} <= set(audit_actions)
        # Draft deletion is supported too.
        assert client.put(pkgurl, headers=admin, json=package).status_code == 200
        draft = client.post('/api/payroll-v2/runs', headers=admin, json={'month': '2026-12'})
        assert draft.status_code == 201, draft.text
        assert client.request('DELETE', f'/api/payroll-v2/runs/{draft.json()["id"]}', headers=admin, json=deletion).status_code == 200
    ui = (Path(__file__).resolve().parent.parent / 'web/src/PayrollExtra.tsx').read_text()
    assert "deletePayrollItem('package',p)" in ui
    assert "deletePayrollItem('adjustment',a)" in ui
    assert "deletePayrollItem('run',r)" in ui
print('Payroll deletion regression passed: admin permissions, confirmation, data integrity, draft/reviewed deletion, published protection and audits.')

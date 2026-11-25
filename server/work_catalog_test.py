"""SQLite integration regression for the real product/project catalog, no live data."""
import os
from pathlib import Path
from tempfile import TemporaryDirectory

from fastapi.testclient import TestClient

with TemporaryDirectory(prefix='hrm-work-catalog-test-') as tmp:
    os.environ.update(
        SASS_HRM_TESTING='1', DB_ENGINE='sqlite',
        DATABASE_PATH=str(Path(tmp) / 'catalog-isolated.db'),
        JWT_SECRET='isolated-product-project-catalog-tests-no-production-use',
    )
    import main
    from mysql_backend import rewrite_sql

    assert rewrite_sql('INSERT INTO t (kind) VALUES(?) ON CONFLICT(kind) DO UPDATE SET cats=excluded.cats') == (
        'INSERT INTO t (kind) VALUES(%s) ON DUPLICATE KEY UPDATE cats=VALUES(cats)'
    )
    with TestClient(main.app) as client:
        password = 'SyntheticCatalogTest-2026!'
        hashed = main.hash_password(password)
        with main.db() as c:
            in_sql = """INSERT INTO employees
              (code,name,email,role,designation,department,location,join_date,password_hash,account_active)
              VALUES(?,?,?,?,?,?,?,?,?,?)"""
            for key, role, active in [('admin', 'admin', 1), ('staff', 'employee', 1),
                                      ('manager', 'manager', 1), ('inactive', 'employee', 0)]:
                c.execute(in_sql, (key, key.title(), f'{key}@test.invalid', role, 'Test', 'QA',
                                   'Isolated', '2026-01-01', hashed, active))
            staff_id = c.execute("SELECT id FROM employees WHERE code='staff'").fetchone()[0]
            inactive_id = c.execute("SELECT id FROM employees WHERE code='inactive'").fetchone()[0]

        def headers_for(name):
            response = client.post('/api/auth/login', json={'email': f'{name}@test.invalid', 'password': password})
            assert response.status_code == 200, response.text
            return {'Authorization': 'Bearer ' + response.json()['token']}

        admin, staff, manager = map(headers_for, ('admin', 'staff', 'manager'))

        def request(method, path='', body=None, status=200, headers=admin):
            r = client.request(method, '/api/catalog/' + path, headers=headers, json=body)
            assert r.status_code == status, r.text
            return r.json()

        for role_headers, code in [({}, 401), (staff, 403), (manager, 403)]:
            for method, path in [('GET', 'projects'), ('POST', 'products'), ('GET', 'products/settings'),
                                 ('PUT', 'projects/settings'), ('PUT', 'products/1'), ('DELETE', 'projects/1')]:
                request(method, path, headers=role_headers, status=code)

        assert request('GET', 'products') == []
        assert request('GET', 'projects') == []
        assert request('GET', 'products/settings') == {'default_status': 'Active', 'categories': []}
        assert request('GET', 'projects/settings') == {'default_status': 'Planned', 'categories': []}
        settings = {'default_status': 'Inactive', 'categories': ['  Software  ', 'Services']}
        assert request('PUT', 'products/settings', settings) == {'default_status': 'Inactive', 'categories': ['Software', 'Services']}
        assert request('GET', 'products/settings')['categories'] == ['Software', 'Services']
        request('PUT', 'products/settings', {'default_status': 'Planned', 'categories': []}, 422)
        request('PUT', 'products/settings', {'default_status': 'Active', 'categories': ['Software','software']}, 422)
        request('PUT', 'projects/settings', {'default_status': 'On Hold', 'categories': ['Operations']})

        product = {'code': 'work-001', 'name': 'Test product', 'category': 'software'}
        first = request('POST', 'products', product, 201)
        assert first == {'id': first['id'], **product, 'code': 'WORK-001', 'category': 'Software',
                         'description': '', 'status': 'Inactive', 'owner_id': None, 'start_date': None, 'end_date': None}
        ppath = f"products/{first['id']}"
        request('POST', 'products', {**product, 'code': 'Work-001'}, 409)
        request('POST', 'products', {**product, 'code': 'space not allowed'}, 422)
        request('POST', 'products', {**product, 'code': 'WORK-002', 'owner_id': staff_id}, 422)
        request('POST', 'products', {**product, 'code': 'WORK-002', 'category': 'Unknown'}, 422)

        project = {'code': 'WORK-001', 'name': 'Test project', 'description': 'Test description', 'category': 'Operations',
                   'owner_id': staff_id, 'start_date': '2026-01-01', 'end_date': '2026-03-01'}
        second = request('POST', 'projects', project, 201)
        jpath = f"projects/{second['id']}"
        assert second == {'id': second['id'], **project, 'status': 'On Hold'}
        assert request('GET', 'projects') == [second]
        request('PUT', jpath, {**project, 'owner_id': inactive_id}, 422)
        request('PUT', jpath, {**project, 'owner_id': 999999}, 422)
        request('PUT', jpath, {**project, 'end_date': '2025-12-01'}, 422)
        request('PUT', jpath, {**project, 'end_date': '2026-02-30'}, 422)
        request('PUT', jpath, {**project, 'status': 'Inactive'}, 422)
        saved = request('PUT', jpath, {**project, 'name': 'Updated project', 'status': 'Completed'})
        assert saved['status'] == 'Completed'
        assert request('GET', 'projects')[0]['name'] == 'Updated project'
        request('DELETE', f"products/{second['id']}", status=404)

        # Retiring a category does not erase the category of a saved record.
        request('PUT', 'products/settings', {'default_status': 'Active', 'categories': []})
        assert request('PUT', ppath, {**product, 'name': 'Updated product'})['category'] == 'Software'
        request('POST', 'products', {**product, 'code': 'WORK-002'}, 422)

        assert request('DELETE', jpath) == {'id': second['id'], 'deleted': True}
        assert request('GET', 'projects') == []
        request('DELETE', jpath, status=404)
        request('PUT', jpath, project, 404)
        request('POST', 'projects', project, 409)
        assert request('DELETE', ppath) == {'id': first['id'], 'deleted': True}
        assert request('GET', 'products') == []

        with main.db() as c:
            assert c.execute('SELECT COUNT(*) FROM hrm_work_catalog WHERE archived_at IS NOT NULL').fetchone()[0] == 2
            assert c.execute("SELECT COUNT(*) FROM audit_events WHERE action LIKE 'catalog.record.%'").fetchone()[0] == 6
            assert c.execute("SELECT COUNT(*) FROM audit_events WHERE action='catalog.settings.update'").fetchone()[0] == 3
            assert c.execute('SELECT COUNT(*) FROM assets').fetchone()[0] == 0
    # Opening the same database again verifies the additive bootstrap is idempotent.
    with TestClient(main.app), main.db() as c:
        assert c.execute('SELECT COUNT(*) FROM hrm_work_catalog').fetchone()[0] == 2

print('PASS: products and projects CRUD, settings, defaults, owner and date integrity, role checks, auditing and database preservation')

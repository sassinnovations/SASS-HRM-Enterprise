"""Isolated offline integration coverage for consolidated settings and missing CRUD operations."""
import os
import sys
import tempfile
from datetime import date, timedelta
from pathlib import Path
from unittest.mock import patch

os.environ['SASS_HRM_TESTING'] = '1'
os.environ['DB_ENGINE'] = 'sqlite'
os.environ['JWT_SECRET'] = 'feature-consolidation-test-secret-never-use-in-production-123456'

from fastapi.testclient import TestClient

with tempfile.TemporaryDirectory() as folder:
    os.environ['DATABASE_PATH'] = str(Path(folder) / 'feature_test.sqlite3')
    import main
    import create_admin
    with TestClient(main.app) as client:
        with patch.object(sys, 'argv', ['create_admin.py', '--email', 'admin@example.org', '--name', 'HR Admin', '--code', 'ADM002', '--location', 'Hyderabad']), patch.object(create_admin.getpass, 'getpass', side_effect=['StrongAdminPassword123!!!'] * 2):
            create_admin.main()
        response = client.post('/api/auth/login', json={'email': 'admin@example.org', 'password': 'StrongAdminPassword123!!!'})
        assert response.status_code == 200, response.text
        hdr = {'Authorization': 'Bearer ' + response.json()['token']}
        with main.db() as c:
            c.execute('''INSERT INTO employees(code,name,email,role,designation,department,location,work_mode,join_date,manager_id,password_hash,account_active)
                         VALUES(?,?,?,?,?,?,?,?,?,?,?,1)''', ('TEST01', 'Test Staff', 'staff@example.org', 'employee', 'Analyst', 'Engineering', 'Unassigned', 'Hybrid', '2025-01-15', None, main.hash_password('StrongTestPassword123!!!')))
            employee_id = c.execute('SELECT id FROM employees WHERE code=?', ('TEST01',)).fetchone()[0]
        user = client.post('/api/auth/login', json={'email': 'staff@example.org', 'password': 'StrongTestPassword123!!!'})
        assert user.status_code == 200, user.text
        staff_hdr = {'Authorization': 'Bearer ' + user.json()['token']}
        future = (date.today() + timedelta(days=10)).isoformat()
        alternate = (date.today() + timedelta(days=11)).isoformat()
        past = (date.today() - timedelta(days=10)).isoformat()

        office = {'code': 'HYD-01', 'name': 'Example Office', 'city': 'Hyderabad', 'country': 'India', 'address': '', 'timezone': 'Asia/Kolkata', 'is_active': True}
        assert client.post('/api/admin/organization/offices', json=office, headers=hdr).status_code == 201
        office_id = client.get('/api/admin/organization/offices', headers=hdr).json()[0]['id']
        delete_url = f'/api/admin/organization/offices/{office_id}'
        delete = {'confirm': 'DELETE', 'reason': 'Duplicate office cleaned up'}
        assert client.request("DELETE", delete_url, json=delete).status_code == 401
        assert client.request("DELETE", delete_url, json=delete, headers=staff_hdr).status_code == 403
        assert client.request("DELETE", delete_url, json={**delete, 'confirm': 'yes'}, headers=hdr).status_code == 422
        assert client.request("DELETE", delete_url, json={**delete, 'reason': 'no'}, headers=hdr).status_code == 422
        with main.db() as c:
            c.execute('UPDATE employees SET location=? WHERE id=?', ('Example Office', employee_id))
        assert client.request("DELETE", delete_url, json=delete, headers=hdr).status_code == 409
        with main.db() as c:
            c.execute('UPDATE employees SET location=? WHERE id=?', ('Unassigned', employee_id))
        with main.db() as c:
            c.execute('INSERT INTO departments(name,location) VALUES(?,?)', ('Office Dependent Team', 'Example Office'))
        assert client.request('DELETE', delete_url, json=delete, headers=hdr).status_code == 409
        assert client.put(delete_url, json={**office, 'name': 'Office Renamed'}, headers=hdr).status_code == 409
        with main.db() as c:
            c.execute('DELETE FROM departments WHERE name=?', ('Office Dependent Team',))
        assert client.request('DELETE', delete_url, json=delete, headers=hdr).status_code == 200
        assert client.get('/api/admin/organization/offices', headers=hdr).json() == []

        shift = {'name': 'Night Shift', 'start_time': '19:00', 'end_time': '03:00', 'location': 'Head Office'}
        created = client.post('/api/shifts', headers=hdr, json=shift)
        assert created.status_code == 201, created.text
        shift_id = created.json()['id']
        shift_url = f'/api/shifts/{shift_id}'
        assert client.put(shift_url, json={**shift, 'name': 'Evening Shift'}, headers=staff_hdr).status_code == 403
        assert client.put(shift_url, json={**shift, 'name': 'Evening Shift'}, headers=hdr).status_code == 200
        assert client.put(shift_url, json={**shift, 'start_time': '03:00', 'end_time': '03:00'}, headers=hdr).status_code == 422
        assert client.put('/api/shifts/999999', json=shift, headers=hdr).status_code == 404
        assignment = {'employee_id': employee_id, 'shift_id': shift_id, 'work_day': future}
        booked = client.post('/api/schedule', json=assignment, headers=hdr)
        assert booked.status_code == 201, booked.text
        assignment_id = booked.json()['id']
        schedule_url = f'/api/schedule/{assignment_id}'
        assert client.put(shift_url, json=shift, headers=hdr).status_code == 409
        assert client.request("DELETE", shift_url, json=delete, headers=hdr).status_code == 409
        assert client.put(schedule_url, json={**assignment, 'work_day': alternate}, headers=hdr).status_code == 200
        assert client.get('/api/schedule', headers=hdr).json()[0]['work_day'][:10] == alternate
        assert client.put(schedule_url, json=assignment, headers=staff_hdr).status_code == 403
        assert client.request("DELETE", schedule_url, json=delete, headers=staff_hdr).status_code == 403
        assert client.put(schedule_url, json={**assignment, 'work_day': past}, headers=hdr).status_code == 422
        assert client.request("DELETE", schedule_url, json={**delete, 'confirm': 'no'}, headers=hdr).status_code == 422
        assert client.request('DELETE', schedule_url, json=delete, headers=hdr).status_code == 200
        # Historical data is protected even though managers may edit future rosters.
        older = client.post('/api/schedule', json={**assignment, 'work_day': past}, headers=hdr)
        assert older.status_code == 201, older.text
        older_url = f'/api/schedule/{older.json()["id"]}'
        assert client.put(older_url, json={**assignment, 'work_day': future}, headers=hdr).status_code == 409
        assert client.request('DELETE', older_url, json=delete, headers=hdr).status_code == 409
        # Clear isolated test fixture directly; production API deliberately forbids historical deletion.
        with main.db() as c:
            c.execute('DELETE FROM shift_assignments WHERE id=?', (older.json()['id'],))
        assert client.request('DELETE', shift_url, json=delete, headers=hdr).status_code == 200
        assert not client.get('/api/shifts', headers=hdr).json()
        with main.db() as c:
            actions = [r[0] for r in c.execute('SELECT action FROM audit_events').fetchall()]
            for action in ('organization.office.deleted', 'shift.updated', 'shift.deleted', 'shift.assigned', 'shift.assignment.updated', 'shift.assignment.deleted'):
                assert action in actions, (action, actions)
        print('PASS: office deletion safeguards, shift CRUD, roster CRUD, authorization, validation, historical protection, audit records')

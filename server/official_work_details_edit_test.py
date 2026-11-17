"""Regression test: HR-admin official work details edits, security and persistence.
Run with: python server/official_work_details_edit_test.py
"""
from pathlib import Path
import os
import tempfile

os.environ['SASS_HRM_TESTING'] = '1'
os.environ['DB_ENGINE'] = 'sqlite'
os.environ['JWT_SECRET'] = 'ISOLATED-OFFICIAL-HR-DETAILS-EDIT-TEST-SECRET-45-CHARS'

from fastapi.testclient import TestClient

with tempfile.TemporaryDirectory() as folder:
    os.environ['DATABASE_PATH'] = str(Path(folder) / 'official-work-details.db')
    import main

    with TestClient(main.app) as client:
        password = 'ValidStrongPass123!'
        with main.db() as db:
            for code, name, email, role in [
                ('SASS-ADMIN-RESET', 'Administrator One', 'admin@example.org', 'admin'),
                ('SASS-EMP-1', 'Employee One', 'one@example.org', 'employee'),
                ('SASS-EMP-2', 'Employee Two', 'two@example.org', 'employee'),
            ]:
                db.execute('''INSERT INTO employees
                    (code,name,email,work_email,role,designation,department,location,work_mode,join_date,password_hash,account_active)
                    VALUES(?,?,?,?,?,?,?,?,?,?,?,1)''', (
                    code,name,email,email,role,'HR Administrator' if role=='admin' else 'Associate',
                    'Human Resources' if role=='admin' else 'Operations','Hyderabad','On-site',
                    '2026-11-14',main.hash_password(password)))
        def login(email):
            result = client.post('/api/auth/login', json={'email': email, 'password':password})
            assert result.status_code == 200, result.text
            return {'Authorization': 'Bearer ' + result.json()['token']}

        admin = login('admin@example.org')
        staff = login('one@example.org')
        base = {
            'code':'SASS-ADMIN-RESET', 'name':'Administrator One', 'email':'admin@example.org',
            'work_email':'admin@example.org', 'designation':'HR Administrator',
            'department':'Human Resources', 'location':'Hyderabad', 'work_mode':'On-site',
            'join_date':'2026-11-14', 'change_reason':'Correct the official staff record'
        }
        endpoint='/api/admin/accounts/1/profile'
        assert client.patch(endpoint, json=base).status_code==401
        assert client.patch(endpoint, headers=staff, json=base).status_code==403
        assert client.patch(endpoint, headers=admin, json={**base,'role':'employee'}).status_code==422
        assert client.patch(endpoint, headers=admin, json={**base,'password_hash':'oops'}).status_code==422
        assert client.patch(endpoint, headers=admin, json={**base,'code':'!bad-code'}).status_code==422
        assert client.patch(endpoint, headers=admin, json={**base,'join_date':'not a date'}).status_code==422
        assert client.patch(endpoint, headers=admin, json={**base,'code':'SASS-EMP-1'}).status_code==409
        assert client.patch(endpoint, headers=admin, json={**base,'work_email':'one@example.org'}).status_code==409
        assert client.patch(endpoint, headers=admin, json={**base,'code':'SASS-NEW-2026','change_reason':'no'}).status_code==422

        changed=client.patch(endpoint, headers=admin, json={**base,
            'code':'SASS-ADMIN-UPDATED','name':'Officially Updated', 'designation':'HR Manager',
            'department':'People Operations','location':'Secunderabad','work_mode':'Hybrid',
            'join_date':'2026-11-12','change_reason':'HR verified work record correction'
        })
        assert changed.status_code==200,changed.text
        assert changed.json()['sessions_revoked'] is False
        assert {'code','name','designation','department','location','work_mode','join_date'} <= set(changed.json()['changed_fields'])
        profile=client.get('/api/profile/me', headers=admin)
        assert profile.status_code==200,profile.text
        assert profile.json()['code']=='SASS-ADMIN-UPDATED'
        assert profile.json()['name']=='Officially Updated'
        assert profile.json()['join_date']=='2026-11-12'
        assert profile.json()['role']=='admin'
        with main.db() as db:
            row=db.execute('SELECT id,role,password_hash,session_version FROM employees WHERE id=1').fetchone()
            assert row['id']==1 and row['role']=='admin' and main.valid_password(password,row['password_hash'])
            assert row['session_version']==0
            audit=db.execute("SELECT details FROM audit_events WHERE action='identity.profile_updated' AND target='employee:1' ORDER BY id DESC LIMIT 1").fetchone()
            assert audit and 'join_date' in audit['details'] and 'HR verified' in audit['details']

        # Existing account administration edit (old payload, no code/date) remains supported.
        legacy={key:base[key] for key in ('name','email','work_email','designation','department','location','work_mode')}
        legacy={**legacy, 'name':'Employee One', 'email':'one@example.org', 'work_email':'one@example.org'}
        updated_other=client.patch('/api/admin/accounts/2/profile',headers=admin,json=legacy)
        assert updated_other.status_code==200,updated_other.text
        with main.db() as db:
            other=db.execute('SELECT code,join_date FROM employees WHERE id=2').fetchone()
            assert other['code']=='SASS-EMP-1' and other['join_date']=='2026-11-14'

        # Work email correction intentionally invalidates the current account JWT.
        mail=client.patch(endpoint,headers=admin,json={**base,
            'code':'SASS-ADMIN-UPDATED', 'name':'Officially Updated','designation':'HR Manager',
            'department':'People Operations','location':'Secunderabad','work_mode':'Hybrid',
            'join_date':'2026-11-12','work_email':'official-new@example.org'
        })
        assert mail.status_code==200,mail.text
        assert mail.json()['sessions_revoked'] is True
        assert client.get('/api/profile/me',headers=admin).status_code==401
        # Work email remains an accepted login identifier.
        changed_session=login('official-new@example.org')
        assert client.get('/api/profile/me', headers=changed_session).json()['work_email']=='official-new@example.org'
        print('PASS: official HR editing, permissions, field validation, code/email conflicts, role protection, join date, legacy compatibility, audit, session revocation')

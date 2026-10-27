"""v4.3 sign-in identities, editable contact fields, developer/HR access and password safety."""
import os, sys, tempfile
from pathlib import Path
from unittest.mock import patch
os.environ['SASS_HRM_TESTING']='1'
os.environ['DB_ENGINE']='sqlite'
os.environ['JWT_SECRET']='TEST-ONLY-account-identity-v43-is-not-a-production-secret'
from fastapi.testclient import TestClient
with tempfile.TemporaryDirectory() as folder:
    os.environ['DATABASE_PATH']=str(Path(folder)/'identity43.db')
    import main,create_admin
    with TestClient(main.app) as client:
        with patch.object(sys,'argv',['create_admin.py','--email','admin@example.org','--name','Root Admin','--code','SASS-ROOT','--location','Hyderabad']),patch.object(create_admin.getpass,'getpass',side_effect=['StrongRootPassword123!']*2):
            create_admin.main()
        def login(mail,pwd):return client.post('/api/auth/login',json={'email':mail,'password':pwd})
        root=login('admin@example.org','StrongRootPassword123!')
        assert root.status_code==200,root.text
        admin={'Authorization':'Bearer '+root.json()['token']}
        payload={'name':'Staff Member','email':'stafflogin@example.org','work_email':'staff.work@example.org',
                 'designation':'Associate','department':'Engineering','location':'Bengaluru','work_mode':'Hybrid',
                 'role':'employee','initial_password':'StaffStrongPassword123!'}
        assert client.post('/api/admin/accounts/create',json=payload).status_code==401
        created=client.post('/api/admin/accounts/create',headers=admin,json=payload)
        assert created.status_code==201,created.text
        eid=created.json()['id']
        with main.db() as db:
            saved=db.execute('SELECT id,code,email,work_email,password_hash,location FROM employees WHERE id=?',(eid,)).fetchone()
            assert saved['id']==eid and saved['code'].startswith('SASS-')
            assert saved['work_email']==payload['work_email'] and saved['location']=='Bengaluru'
            assert payload['initial_password'] not in saved['password_hash']
            assert '$' in saved['password_hash']
        a=login('stafflogin@example.org',payload['initial_password']); b=login('staff.work@example.org',payload['initial_password'])
        assert a.status_code==200 and b.status_code==200
        staff={'Authorization':'Bearer '+a.json()['token']}
        assert client.get('/api/auth/me',headers=staff).json()['work_email']==payload['work_email']
        assert client.patch(f'/api/admin/accounts/{eid}/profile',headers=staff,json={k:payload[k] for k in ('name','email','work_email','designation','department','location','work_mode')}).status_code==403
        accounts=client.get('/api/admin/accounts',headers=admin)
        assert accounts.status_code==200
        listed=next(x for x in accounts.json() if x['id']==eid)
        assert listed['work_email']==payload['work_email'] and listed['code']==saved['code']
        assert 'password_hash' not in str(accounts.json()) and 'initial_password' not in str(accounts.json())
        duplicate=client.post('/api/admin/accounts/create',headers=admin,json={**payload,'email':'staff.work@example.org','work_email':'another@example.org'})
        assert duplicate.status_code==409,duplicate.text
        edited={k:payload[k] for k in ('name','email','work_email','designation','department','location','work_mode')}
        edited.update(email='newlogin@example.org',work_email='newwork@example.org',location='Hyderabad')
        res=client.patch(f'/api/admin/accounts/{eid}/profile',headers=admin,json=edited)
        assert res.status_code==200 and res.json()['sessions_revoked'] is True,res.text
        assert client.get('/api/auth/me',headers=staff).status_code==401
        assert login('stafflogin@example.org',payload['initial_password']).status_code==401
        assert login('staff.work@example.org',payload['initial_password']).status_code==401
        assert login('newlogin@example.org',payload['initial_password']).status_code==200
        assert login('newwork@example.org',payload['initial_password']).status_code==200
        assert client.patch(f'/api/admin/accounts/{eid}/profile',headers=admin,json={**edited,'email':'admin@example.org'}).status_code==409
        # Developer Admin combines administrator role with a server-side developer grant.
        dev=client.post('/api/admin/accounts/create',headers=admin,json={**payload,'name':'Dev Admin','email':'developer@example.org','work_email':'dev.work@example.org','role':'developer_admin','initial_password':'DevAdminSecurePassword123!'})
        assert dev.status_code==201,dev.text
        did=dev.json()['id']
        with main.db() as db:
            user=db.execute('SELECT role FROM employees WHERE id=?',(did,)).fetchone()
            grant=db.execute('SELECT enabled FROM developer_grants WHERE employee_id=?',(did,)).fetchone()
            assert user['role']=='admin' and grant['enabled']==1
        dev_login=login('dev.work@example.org','DevAdminSecurePassword123!')
        assert dev_login.status_code==200 and dev_login.json()['user']['access_tier']=='developer_admin'
        dev_auth={'Authorization':'Bearer '+dev_login.json()['token']}
        assert client.get('/api/admin/accounts',headers=dev_auth).status_code==200
        hr=client.patch(f'/api/admin/accounts/{did}/role',headers=admin,json={'role':'hr_subadmin'})
        assert hr.status_code==200,hr.text
        assert client.get('/api/admin/accounts',headers=dev_auth).status_code==401
        with main.db() as db:
            assert db.execute('SELECT enabled FROM developer_grants WHERE employee_id=?',(did,)).fetchone()['enabled']==0
        relog=login('developer@example.org','DevAdminSecurePassword123!')
        assert relog.status_code==200 and relog.json()['user']['access_tier']=='hr_subadmin'
        hr_auth={'Authorization':'Bearer '+relog.json()['token']}
        assert client.get('/api/admin/accounts',headers=hr_auth).status_code==403
        assert client.post('/api/admin/accounts/create',headers=hr_auth,json=payload).status_code==403
        with TestClient(main.app) as second:
            assert second.post('/api/auth/login',json={'email':'newwork@example.org','password':payload['initial_password']}).status_code==200
        with main.db() as db:
            assert db.execute('SELECT COUNT(*) FROM audit_events WHERE action=?',('identity.profile_updated',)).fetchone()[0]>=1
        # Alternating aliases must not double the number of allowed login guesses.
        for alias in ['newlogin@example.org','newwork@example.org','newlogin@example.org','newwork@example.org','newlogin@example.org']:
            assert login(alias,'IncorrectPassword123!').status_code==401
        assert login('newwork@example.org',payload['initial_password']).status_code==429
        print('PASS v4.3 account IDs, persistent emails/password hashes, safe edits, developer/HR roles, shared alias throttling')

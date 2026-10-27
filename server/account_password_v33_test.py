"""Isolated account-selector, reusable password and HR sub-admin tier security checks."""
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch
os.environ['SASS_HRM_TESTING']='1'
os.environ['DB_ENGINE']='sqlite'
os.environ['JWT_SECRET']='TEST-ONLY-this-is-over-forty-characters-unique-account-v33'
from fastapi.testclient import TestClient

with tempfile.TemporaryDirectory() as folder:
    os.environ['DATABASE_PATH']=str(Path(folder)/'accounts-v33.db')
    import main, create_admin
    with TestClient(main.app) as client:
        with patch.object(sys,'argv',['create_admin.py','--email','root@example.org','--name','HR Owner','--code','SASS-HR-1','--location','Hyderabad']), patch.object(create_admin.getpass,'getpass',side_effect=['RootStrongTest123!']*2):
            create_admin.main()
        def login(email,pwd):
            return client.post('/api/auth/login',json={'email':email,'password':pwd})
        root=login('root@example.org','RootStrongTest123!')
        assert root.status_code==200,root.text
        admin={'Authorization':'Bearer '+root.json()['token']}
        base={'name':'New Employee','email':'staff@example.org','designation':'Associate','department':'HR','location':'Hyderabad','role':'employee','work_mode':'Hybrid'}
        assert client.post('/api/admin/accounts/create',json={**base,'initial_password':'SecureStaff12345!'}).status_code==401
        assert client.post('/api/admin/accounts/create',headers=admin,json={**base,'initial_password':'short'}).status_code==422
        assert client.post('/api/admin/accounts/create',headers=admin,json={**base,'initial_password':'AlllettersNoDigits'}).status_code==422
        created=client.post('/api/admin/accounts/create',headers=admin,json={**base,'initial_password':'SecureStaff12345!'})
        assert created.status_code==201, created.text
        person_id=created.json()['id']
        assert created.json()['account_active'] is True
        assert 'SecureStaff12345!' not in str(created.json())
        with main.db() as c:
            user=c.execute('SELECT password_hash,role,account_active FROM employees WHERE id=?',(person_id,)).fetchone()
            assert 'SecureStaff12345!' not in user['password_hash']
            assert user['role']=='employee' and user['account_active']==1
        staff=login('staff@example.org','SecureStaff12345!')
        assert staff.status_code==200,staff.text
        staff_header={'Authorization':'Bearer '+staff.json()['token']}
        assert login('staff@example.org','SecureStaff12345!').status_code==200, 'Password must be reusable'
        assert client.get('/api/admin/accounts',headers=staff_header).status_code==403
        assert client.post('/api/admin/accounts/1/set-password',headers=staff_header,json={'new_password':'AttackerPassword123!'}).status_code==403
        # Persistence across new HTTP client sessions using the same saved database.
        with TestClient(main.app) as another_client:
            assert another_client.post('/api/auth/login',json={'email':'staff@example.org','password':'SecureStaff12345!'}).status_code==200
        sub=client.post('/api/admin/accounts/create',headers=admin,json={**base,'name':'HR Sub Admin','email':'sub@example.org','role':'hr_subadmin','initial_password':'SecureSubAdmin123!'})
        assert sub.status_code==201,sub.text
        sid=sub.json()['id']
        with main.db() as c:
            user=c.execute('SELECT role FROM employees WHERE id=?',(sid,)).fetchone()
            tier=c.execute('SELECT tier FROM account_access_tiers WHERE employee_id=?',(sid,)).fetchone()
            assert user['role']=='manager' and tier['tier']=='hr_subadmin'
        sublogin=login('sub@example.org','SecureSubAdmin123!')
        assert sublogin.status_code==200 and sublogin.json()['user']['access_tier']=='hr_subadmin'
        subhead={'Authorization':'Bearer '+sublogin.json()['token']}
        assert client.get('/api/admin/accounts',headers=subhead).status_code==403
        assert client.post('/api/admin/accounts/create',headers=subhead,json={**base,'email':'fake@example.org','role':'admin','initial_password':'SecureStaff12345!'}).status_code==403
        assert client.post(f'/api/admin/accounts/{sid}/set-password',headers=subhead,json={'new_password':'NewSecurePass123!' }).status_code==403
        accounts=client.get('/api/admin/accounts',headers=admin)
        assert accounts.status_code==200
        assert next(x for x in accounts.json() if x['id']==sid)['access_tier']=='hr_subadmin'
        # Admin resets another account. All previous JWTs become invalid.
        old_token=staff_header
        reset=client.post(f'/api/admin/accounts/{person_id}/set-password',headers=admin,json={'new_password':'ReplacedPassword123!'})
        assert reset.status_code==200,reset.text
        assert client.get('/api/auth/me',headers=old_token).status_code==401
        assert login('staff@example.org','SecureStaff12345!').status_code==401
        assert login('staff@example.org','ReplacedPassword123!').status_code==200
        assert client.post('/api/admin/accounts/1/set-password',headers=admin,json={'new_password':'TooManyPermissions123!'}).status_code==409
        changed=client.patch(f'/api/admin/accounts/{sid}/role',headers=admin,json={'role':'employee'})
        assert changed.status_code==200,changed.text
        assert client.get('/api/auth/me',headers=subhead).status_code==401
        with main.db() as c:
            assert c.execute('SELECT role FROM employees WHERE id=?',(sid,)).fetchone()['role']=='employee'
            assert c.execute('SELECT tier FROM account_access_tiers WHERE employee_id=?',(sid,)).fetchone()['tier']=='employee'
            logs=c.execute("SELECT action,details FROM audit_events WHERE action='identity.password_set_by_admin'").fetchall()
            assert logs and all('ReplacedPassword123!' not in str(x) for x in logs)
        print('PASS v3.3 reusable salted passwords, direct creation, role limits, account tier persistence, reset, revocation')

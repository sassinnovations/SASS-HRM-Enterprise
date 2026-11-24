"""Automated, isolated identity-management and recovery security regression tests."""
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

os.environ['SASS_HRM_TESTING'] = '1'
os.environ['DB_ENGINE'] = 'sqlite'
os.environ['JWT_SECRET'] = 'TEST-ONLY-unique-secret-over-40-chars-for-identity-regression-tests'

from fastapi.testclient import TestClient

with tempfile.TemporaryDirectory() as folder:
    os.environ['DATABASE_PATH'] = str(Path(folder) / 'identity-v25.db')
    import main, create_admin, platform_plus, accounts_v25
    with TestClient(main.app) as client:
        assert client.get('/api/health').status_code == 200
        with patch.object(sys,'argv',['create_admin.py','--email','root@example.org','--name','Root Admin','--code','SASS-ADMIN-01','--location','Hyderabad']), patch.object(create_admin.getpass,'getpass',side_effect=['StrongRootPass12345!']*2):
            create_admin.main()
        def login(email,password):
            return client.post('/api/auth/login',json={'email':email,'password':password})
        root_login=login('root@example.org','StrongRootPass12345!')
        assert root_login.status_code==200,root_login.text
        admin={'Authorization': 'Bearer '+root_login.json()['token']}
        assert client.get('/api/admin/accounts',headers=admin).status_code==200
        account={
            'name':'Second Admin','email':'second@example.org','role':'admin','designation':'HR Director',
            'department':'Human Resources','location':'Hyderabad','work_mode':'Hybrid'
        }
        result=client.post('/api/admin/accounts/create',headers=admin,json=account)
        assert result.status_code==201,result.text
        second_id=result.json()['id']
        assert 'password' not in str(result.json()).lower()
        assert login(account['email'],'None').status_code==401
        assert client.post('/api/admin/accounts/create',headers=admin,json=account).status_code==409
        issued={}
        with patch.object(platform_plus,'send_activation_email',side_effect=lambda to,token,expiry:issued.update(email=to,token=token)):
            send=client.post('/api/admin/invitations',headers=admin,json={'employee_id':second_id})
            assert send.status_code==201,send.text
        assert issued['email']=='second@example.org' and 'token' not in str(send.json())
        activated=client.post('/api/auth/activate',json={'token':issued['token'],'new_password':'SecondStrongPassword123!'})
        assert activated.status_code==200,activated.text
        second_login=login('second@example.org','SecondStrongPassword123!')
        assert second_login.status_code==200
        second={'Authorization':'Bearer '+second_login.json()['token']}
        assert client.get('/api/admin/accounts',headers=second).status_code==200
        assert client.patch(f'/api/admin/accounts/{second_id}/role',headers=second,json={'role':'employee'}).status_code==409
        staff_account={**account,'name':'Test Staff','email':'staff@example.org','role':'employee','designation':'Specialist'}
        staff=client.post('/api/admin/accounts/create',headers=admin,json=staff_account)
        assert staff.status_code==201
        staff_id=staff.json()['id']
        delivered={}
        with patch.object(platform_plus,'send_activation_email',side_effect=lambda to,token,expiry:delivered.update(token=token)):
            assert client.post('/api/admin/invitations',headers=admin,json={'employee_id':staff_id}).status_code==201
        assert client.post('/api/auth/activate',json={'token':delivered['token'],'new_password':'EmployeeStrongPassword123!'}).status_code==200
        staff_token=login('staff@example.org','EmployeeStrongPassword123!').json()['token']
        staff_headers={'Authorization':'Bearer '+staff_token}
        assert client.post('/api/admin/accounts/create',headers=staff_headers,json=staff_account).status_code==403
        assert client.patch(f'/api/admin/accounts/{second_id}/role',headers=staff_headers,json={'role':'employee'}).status_code==403
        assert client.post(f'/api/admin/accounts/{second_id}/revoke-sessions',headers=staff_headers).status_code==403
        assert client.patch(f'/api/admin/accounts/{second_id}/developer',headers=staff_headers,json={'enabled':True}).status_code==403
        assert client.patch(f'/api/admin/accounts/{staff_id}/developer',headers=admin,json={'enabled':True}).status_code==422
        # Elevation causes existing tokens to expire and enables admin HR permissions only after re-login.
        elevated=client.patch(f'/api/admin/accounts/{staff_id}/role',headers=admin,json={'role':'manager'})
        assert elevated.status_code==200
        assert client.get('/api/auth/me',headers=staff_headers).status_code==401
        manager_token=login('staff@example.org','EmployeeStrongPassword123!').json()['token']
        manager_headers={'Authorization':'Bearer '+manager_token}
        assert client.get('/api/admin/accounts',headers=manager_headers).status_code==403
        # Disable another admin without shutting down the only administrator.
        assert client.patch(f'/api/admin/accounts/{second_id}/developer',headers=admin,json={'enabled':True}).status_code==200
        assert client.get('/api/auth/me',headers=second).status_code==401
        second={'Authorization':'Bearer '+login('second@example.org','SecondStrongPassword123!').json()['token']}
        assert client.get('/api/developer/status',headers=second).status_code==200
        assert client.patch(f'/api/admin/accounts/{second_id}/developer',headers=admin,json={'enabled':False}).status_code==200
        assert client.get('/api/developer/status',headers=second).status_code==401
        assert client.patch(f'/api/admin/accounts/{second_id}/role',headers=admin,json={'role':'manager'}).status_code==200
        second={'Authorization':'Bearer '+login('second@example.org','SecondStrongPassword123!').json()['token']}
        assert client.get('/api/admin/accounts',headers=second).status_code==403
        assert client.get('/api/developer/status',headers=second).status_code==403
        assert client.patch(f'/api/admin/accounts/{staff_id}/role',headers=admin,json={'role':'admin'}).status_code==200
        # Explicit server-side revoke, not just clearing the browser's token.
        new_staff={'Authorization':'Bearer '+login('staff@example.org','EmployeeStrongPassword123!').json()['token']}
        assert client.post(f'/api/admin/accounts/{staff_id}/revoke-sessions',headers=admin).status_code==200
        assert client.get('/api/auth/me',headers=new_staff).status_code==401
        root_reset_tokens={}
        with patch.object(accounts_v25,'send_reset_email',side_effect=lambda to,token:root_reset_tokens.update(to=to,token=token)):
            forgot=client.post('/api/auth/password-reset/request',json={'email':'ROOT@example.org'})
        assert forgot.status_code==202,forgot.text
        assert root_reset_tokens['token'] not in str(forgot.json()) and 'root@example.org' not in str(forgot.json())
        assert root_reset_tokens['to']=='root@example.org'
        # Rate-limited and enumeration safe responses.
        assert client.post('/api/auth/password-reset/request',json={'email':'unknown@example.org'}).json()==forgot.json()
        with patch.object(accounts_v25,'send_reset_email',side_effect=AssertionError('Cooldown failed')):
            assert client.post('/api/auth/password-reset/request',json={'email':'root@example.org'}).status_code==202
        assert client.post('/api/auth/password-reset/confirm',json={'token':root_reset_tokens['token'],'new_password':'weak'}).status_code==422
        assert client.post('/api/auth/password-reset/confirm',json={'token':'bogus-token-value-of-sufficient-length','new_password':'NewRootPassword9876!'}).status_code==400
        reset=client.post('/api/auth/password-reset/confirm',json={'token':root_reset_tokens['token'],'new_password':'NewRootPassword9876!'})
        assert reset.status_code==200,reset.text
        assert client.post('/api/auth/password-reset/confirm',json={'token':root_reset_tokens['token'],'new_password':'AnotherPassword9876!'}).status_code==400
        assert client.get('/api/auth/me',headers=admin).status_code==401
        # Failed SMTP delivery must never leave a valid reset token or disclose account existence.
        with patch.object(accounts_v25, 'send_reset_email', side_effect=RuntimeError('SMTP failure')):
            no_mail=client.post('/api/auth/password-reset/request',json={'email':'staff@example.org'})
        assert no_mail.status_code==202 and no_mail.json()==forgot.json()
        with main.db() as conn:
            assert conn.execute('SELECT COUNT(*) FROM password_reset_tokens WHERE employee_id=?',(staff_id,)).fetchone()[0]==0
        assert login('root@example.org','StrongRootPass12345!').status_code==401
        admin={'Authorization':'Bearer '+login('root@example.org','NewRootPassword9876!').json()['token']}
        # Prevent suspension of only active administrator, even after the second was demoted.
        assert client.patch('/api/admin/accounts/1',headers=admin,json={'active':False}).status_code==409
        assert client.patch(f'/api/admin/accounts/{staff_id}/role',headers=admin,json={'role':'employee'}).status_code==200
        assert client.get('/api/developer/status',headers=new_staff).status_code==401
        logout=client.post('/api/auth/logout',headers=admin)
        assert logout.status_code==200,logout.text
        assert client.get('/api/auth/me',headers=admin).status_code==401
        with main.db() as conn:
            logged=main.rows(conn.execute("SELECT action FROM audit_events WHERE action LIKE 'identity.%' OR action LIKE 'auth.%'"))
            assert len(logged)>=8
            assert all(len(str(r['action'])) > 0 for r in logged)
        print('PASS: v2.5 account creation, invite activation, admin/manager RBAC, role change, developer grant, JWT revocation, reset single-use, logout, audit, password protection')

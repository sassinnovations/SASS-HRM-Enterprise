"""Synthetic-free initialization + auth bootstrap + SMTP invitation contract on a test-only SQLite database."""
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

os.environ['SASS_HRM_TESTING']='1'
os.environ['DB_ENGINE']='sqlite'
os.environ['JWT_SECRET']='test-only-long-random-placeholder-at-least-40-characters-1234'

from fastapi.testclient import TestClient

with tempfile.TemporaryDirectory() as scratch:
    os.environ['DATABASE_PATH']=str(Path(scratch)/'empty.db')
    import main
    import create_admin
    import platform_plus
    with TestClient(main.app) as client:
        assert client.get('/api/health').json()['database']=='sqlite'
        with main.db() as db:
            assert db.execute('SELECT COUNT(*) FROM employees').fetchone()[0] == 0, 'Seeder created employee'
            assert db.execute('SELECT COUNT(*) FROM policies').fetchone()[0] == 0, 'Seeder created policies'
            assert db.execute('SELECT COUNT(*) FROM departments').fetchone()[0] == 0, 'Seeder created departments'
            assert db.execute('SELECT COUNT(*) FROM leave_entitlements').fetchone()[0] == 0
            assert db.execute('SELECT COUNT(*) FROM benefit_plans').fetchone()[0] == 0
        assert client.post('/api/auth/login',json={'email':'admin@demo.sass.local','password':'Demo@12345'}).status_code==401
        with patch.object(sys,'argv',['create_admin.py','--email','hr@sass-innovations.example','--name','HR Administrator','--code','SASS-HR-001','--location','Hyderabad']), patch.object(create_admin.getpass,'getpass',side_effect=['StrongInitialPassword987!','StrongInitialPassword987!']):
            create_admin.main()
        with patch.object(sys,'argv',['create_admin.py','--email','hr2@sass-innovations.example','--name','Other Admin','--code','SASS-HR-002','--location','Chennai']),patch.object(create_admin.getpass,'getpass',side_effect=['StrongInitialPassword987!','StrongInitialPassword987!']):
            try:create_admin.main();raise AssertionError('second bootstrap allowed')
            except SystemExit as e:assert 'only' in str(e)
        r=client.post('/api/auth/login',json={'email':'hr@sass-innovations.example','password':'StrongInitialPassword987!'})
        assert r.status_code==200, r.text
        h={'Authorization':'Bearer '+r.json()['token']}
        assert client.get('/api/auth/me',headers=h).status_code==200
        assert client.get('/api/employees',headers=h).status_code==200
        assert len(client.get('/api/employees',headers=h).json())==1
        assert client.get('/api/organization/departments',headers=h).json()==[]
        assert client.get('/api/policies',headers=h).json()==[]
        employee=client.post('/api/employees',headers=h,json={'name':'New Employee','email':'staff@sass-innovations.example','designation':'Staff Engineer','department':'Engineering','location':'Hyderabad','role':'employee'})
        assert employee.status_code==201, employee.text
        employee_id=employee.json()['id']
        assert client.post('/api/auth/login',json={'email':'staff@sass-innovations.example','password':'Demo@12345'}).status_code==401
        assert client.post('/api/admin/invitations',headers=h,json={'employee_id':employee_id}).status_code==503, 'Invite should require SMTP configuration'
        delivery={}
        def fake_email(to,token,expiry):delivery.update(to=to,token=token,expiry=expiry)
        with patch.object(platform_plus,'send_activation_email',side_effect=fake_email):
            invitation=client.post('/api/admin/invitations',headers=h,json={'employee_id':employee_id})
        assert invitation.status_code==201,invitation.text
        assert 'activation_token' not in invitation.json(), 'Never leak invitation secrets in API'
        assert delivery['to']=='staff@sass-innovations.example'
        result=client.post('/api/auth/activate',json={'token':delivery['token'],'new_password':'EmployeeStrongerPassword987!'})
        assert result.status_code==200,result.text
        session=client.post('/api/auth/login',json={'email':'staff@sass-innovations.example','password':'EmployeeStrongerPassword987!'})
        assert session.status_code==200
        eh={'Authorization':'Bearer '+session.json()['token']}
        assert client.get('/api/admin/accounts',headers=eh).status_code==403
        assert client.post('/api/vault/files',headers=eh,json={'employee_id':employee_id,'filename':'doc.txt','mime_type':'text/plain','category':'Other','data_base64':'SGVsbG8='}).status_code==503
        print('PASS: empty DB, no demo login, one-time admin, auth, employee invitation via SMTP-only contract, activation, permissions, vault fail-closed')

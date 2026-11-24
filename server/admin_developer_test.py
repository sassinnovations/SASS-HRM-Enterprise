"""Isolated, synthetic-only tests for dual administrator/developer entitlement."""
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

os.environ['SASS_HRM_TESTING']='1'
os.environ['DB_ENGINE']='sqlite'
os.environ['JWT_SECRET']='test-only-long-random-placeholder-at-least-40-characters-1234'

with tempfile.TemporaryDirectory() as scratch:
    os.environ['DATABASE_PATH']=str(Path(scratch)/'sass_test.db')
    from fastapi.testclient import TestClient
    import main, create_admin, developer_access
    with TestClient(main.app) as client:
        assert client.get('/api/developer/status').status_code in (401,403)
        with patch.object(sys,'argv',['create_admin.py','--email','hr-admin@company.example','--developer','--name','Sample Admin','--code','SASS-ADM-001','--location','Hyderabad']),patch.object(create_admin.getpass,'getpass',side_effect=['UniqueTestPass987!','UniqueTestPass987!']):
            create_admin.main()
        with main.db() as c:
            records=main.rows(c.execute('SELECT e.email,g.enabled FROM employees e JOIN developer_grants g ON e.id=g.employee_id'))
            assert len(records)==1 and records[0]['enabled']==1
            assert records[0]['email']=='hr-admin@company.example'
            assert c.execute('SELECT COUNT(*) FROM employees').fetchone()[0]==1
        result=client.post('/api/auth/login',json={'email':'hr-admin@company.example','password':'UniqueTestPass987!'})
        assert result.status_code==200,result.text
        assert result.json()['user']['developer_access'] is True
        headers={'Authorization': 'Bearer '+result.json()['token']}
        assert client.get('/api/auth/me',headers=headers).json()['developer_access'] is True
        report=client.get('/api/developer/status',headers=headers)
        assert report.status_code==200,report.text
        assert report.json()['database_status']=='connected'
        assert 'password' not in report.text.lower() and 'jwt' not in report.text.lower()
        employee=client.post('/api/employees',headers=headers,json={'name':'Demo Staff','email':'staff@sass-innovations.example','designation':'Associate','department':'Operations','location':'Hyderabad','role':'employee'})
        assert employee.status_code==201,employee.text
        with main.db() as c:
            c.execute('UPDATE employees SET password_hash=?, account_active=1 WHERE email=?',(main.hash_password('StaffPassword987!'),'staff@sass-innovations.example'))
        staff=client.post('/api/auth/login',json={'email':'staff@sass-innovations.example','password':'StaffPassword987!'})
        assert staff.status_code==200
        staff_h={'Authorization':'Bearer '+staff.json()['token']}
        assert staff.json()['user']['developer_access'] is False
        assert client.get('/api/developer/status',headers=staff_h).status_code==403
        with main.db() as c:
            c.execute('UPDATE developer_grants SET enabled=0')
        assert client.get('/api/developer/status',headers=headers).status_code==403
        assert client.get('/api/auth/me',headers=headers).json()['developer_access'] is False
        print('PASS: one admin + separate developer grant, authenticated status, employee forbidden, revocation effective, no secrets')

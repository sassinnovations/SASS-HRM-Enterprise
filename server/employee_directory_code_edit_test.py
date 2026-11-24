"""Isolated HRIS employee Edit regression: code SASS0047 and related settings.
Run: python server/employee_directory_code_edit_test.py
No production database or accounts are touched.
"""
import os
import tempfile
from pathlib import Path

os.environ['SASS_HRM_TESTING']='1'
os.environ['DB_ENGINE']='sqlite'
os.environ['JWT_SECRET']='LOCAL-TEST-EMPLOYEE-DIRECTORY-CODE-EDIT-LONG-SECRET-2026'

from fastapi.testclient import TestClient

with tempfile.TemporaryDirectory() as temp:
    os.environ['DATABASE_PATH']=str(Path(temp)/'employee-directory-edit.db')
    import main

    password='ComplexTestPassword123!'
    with TestClient(main.app) as client:
        with main.db() as conn:
            for code,name,email,role,manager in [
                ('SASS-ADM-1','HR Admin','admin@test.example','admin',None),
                ('SASS-EMP-1','First Employee','one@test.example','employee',1),
                ('SASS-EMP-2','Second Employee','two@test.example','employee',1),
                ('SASS-MGR-1','Reporting Manager','manager@test.example','manager',1),
            ]:
                conn.execute('''INSERT INTO employees
                (code,name,email,work_email,role,designation,department,location,
                 work_mode,join_date,manager_id,password_hash,account_active)
                VALUES(?,?,?,?,?,?,?,?,?,?,?,?,1)''',
                (code,name,email,email,role,'Associate','Operations','Hyderabad',
                 'Hybrid','2026-11-14',manager,main.hash_password(password)))
            # A linked record must still point to the exact same employee ID after code edits.
            conn.execute("INSERT INTO attendance(employee_id,day,status) VALUES(2,'2026-11-18','Present')")

        def token(email):
            response=client.post('/api/auth/login',json={'email':email,'password':password})
            assert response.status_code==200,response.text
            return {'Authorization':'Bearer '+response.json()['token']}

        admin=token('admin@test.example')
        staff=token('one@test.example')
        path='/api/employees/2'
        assert client.patch(path,json={'code':'SASS0047','change_reason':'Code correction'}).status_code==401
        assert client.patch(path,headers=staff,json={'code':'SASS0047','change_reason':'Code correction'}).status_code==403
        for bad in ({'code':'!invalid','change_reason':'Code correction'},
                    {'code':'SASS0047','change_reason':'no'},
                    {'join_date':'invalid-date','change_reason':'Valid reason'},
                    {'role':'admin'},{'password_hash':'unsafe'},
                    {'id':100}, {'account_active':False}):
            assert client.patch(path,headers=admin,json=bad).status_code==422,bad
        assert client.patch(path,headers=admin,json={'code':'sass-emp-2','change_reason':'Code correction'}).status_code==409
        assert client.patch(path,headers=admin,json={'work_email':'two@test.example'}).status_code==409
        assert client.patch(path,headers=admin,json={'manager_id':2}).status_code==422
        assert client.patch(path,headers=admin,json={'manager_id':999}).status_code==422

        change=client.patch(path,headers=admin,json={
            'code':'SASS0047',
            'name':'Employee Official Name',
            'designation':'Associate Software Engineer',
            'department':'IT Department',
            'location':'Hyderabad',
            'work_mode':'On-site',
            'join_date':'2026-04-01',
            'manager_id':4,
            'change_reason':'Verified original staff code',
        })
        assert change.status_code==200,change.text
        data=change.json()
        assert data['status']=='updated' and data['sessions_revoked'] is False
        assert {'code','name','designation','department','work_mode','join_date','manager_id'}<=set(data['changed_fields'])
        directory=client.get('/api/employees',headers=staff)
        assert directory.status_code==200
        employee=next(r for r in directory.json() if r['id']==2)
        assert employee['code']=='SASS0047' and employee['name']=='Employee Official Name'
        assert employee['manager_id']==4 and employee['join_date']=='2026-04-01'
        assert employee['role']=='employee'
        with main.db() as conn:
            assert conn.execute('SELECT employee_id FROM attendance WHERE day=?',('2026-11-18',)).fetchone()['employee_id']==2
            evidence=conn.execute("SELECT details FROM audit_events WHERE action='employee.updated' AND target='employee:2' ORDER BY id DESC LIMIT 1").fetchone()
            assert evidence and 'SASS-EMP-1 -> SASS0047' in evidence['details']
            assert 'Verified original staff code' in evidence['details']
            assert main.valid_password(password,conn.execute('SELECT password_hash FROM employees WHERE id=2').fetchone()['password_hash'])

        # An empty manager choice must actually clear the reporting line.
        clear=client.patch(path,headers=admin,json={'manager_id':None})
        assert clear.status_code==200,clear.text
        assert next(r for r in client.get('/api/employees',headers=admin).json() if r['id']==2)['manager_id'] is None
        # Legacy partial patches still work unchanged.
        old_style=client.patch(path,headers=admin,json={'designation':'Engineer'})
        assert old_style.status_code==200,old_style.text

        # Email edits revoke this employee's JWT; editing staff code alone does not.
        assert client.get('/api/auth/me',headers=staff).status_code==200
        mail=client.patch(path,headers=admin,json={'work_email':'official@test.example','email':'official@test.example'})
        assert mail.status_code==200,mail.text
        assert mail.json()['sessions_revoked'] is True
        assert client.get('/api/auth/me',headers=staff).status_code==401
        new_staff=token('official@test.example')
        assert client.get('/api/auth/me',headers=new_staff).json()['code']=='SASS0047'
        assert client.patch(path,headers=admin,json={'code':'SASS0047','change_reason':''}).json()['status']=='unchanged'
        print('PASS: SASS0047 code editing, all HRIS fields, manager clear, validation, duplicates, access, linked records, audit, session revocation')

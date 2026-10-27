"""v3.6 leave coverage and HR task templates, isolated SQLite data only."""
import os
import tempfile
from pathlib import Path
from datetime import date, timedelta
from fastapi.testclient import TestClient
os.environ.update(SASS_HRM_TESTING='1', DB_ENGINE='sqlite', JWT_SECRET='test-v36-secret-created-for-isolated-workforce-coverage-test-1234567890')
with tempfile.TemporaryDirectory() as d:
    os.environ['DATABASE_PATH']=str(Path(d)/'test.sqlite')
    import main
    with TestClient(main.app) as client:
        with main.db() as c:
            ids={}
            for code,role,manager,dept in [('ADMIN','admin',None,'People'),('MGR','manager',None,'Engineering'),('ONE','employee','MGR','Engineering'),('TWO','employee',None,'Finance'),('OFF','employee','MGR','Engineering')]:
                manager_id=ids.get(manager)
                r=c.execute('''INSERT INTO employees(code,name,email,role,designation,department,location,join_date,password_hash,account_active,manager_id)
                     VALUES(?,?,?,?,?,?,?,?,?,?,?)''',(code,code+' Name',code.lower()+'@example.invalid',role,'Analyst',dept,'Hyderabad',date.today().isoformat(),main.hash_password('Safe-Example-Password-123'),0 if code=='OFF' else 1,manager_id))
                ids[code]=r.lastrowid
            start=date.today().replace(day=1)
            end=start+timedelta(days=1)
            for code,state,reason in [('ONE','Approved','Medical details not to expose'),('TWO','Approved','Private family reason'),('MGR','Pending','private manager reason'),('OFF','Approved','inactive leave')]:
                c.execute('''INSERT INTO leave_requests(employee_id,start_date,end_date,leave_type,reason,days,status,created_at)
                       VALUES(?,?,?,?,?,?,?,?)''',(ids[code],start.isoformat(),end.isoformat(),'Casual',reason,2,state,start.isoformat()))
            c.execute('INSERT INTO holidays(name,day,location) VALUES(?,?,?)',('Office holiday',start.isoformat(),'All'))
        def login(code):
            r=client.post('/api/auth/login',json={'email':code.lower()+'@example.invalid','password':'Safe-Example-Password-123'})
            assert r.status_code==200,r.text
            return {'Authorization':'Bearer '+r.json()['token']}
        admin=login('ADMIN');manager=login('MGR');one=login('ONE');two=login('TWO')
        month=start.strftime('%Y-%m')
        path=f'/api/workforce/leave-coverage?month={month}'
        assert client.get(path).status_code==401
        assert client.get('/api/workforce/leave-coverage?month=2026-13',headers=one).status_code==422
        r=client.get(path,headers=one)
        assert r.status_code==200,r.text
        assert r.json()['scope']=='personal' and r.json()['summary']['people_with_leave']==1
        assert {x['employee_name'] for day in r.json()['days'] for x in day['on_leave']}=={'ONE Name'}
        assert 'reason' not in r.text and 'Medical details' not in r.text
        assert client.get(path+'&department=Finance',headers=one).status_code==403
        team=client.get(path,headers=manager).json()
        assert team['scope']=='team' and team['summary']['people_with_leave']==1
        assert {x['employee_name'] for day in team['days'] for x in day['on_leave']}=={'ONE Name'}
        assert client.get(path+'&department=Engineering',headers=manager).status_code==403
        org=client.get(path,headers=admin).json()
        assert org['summary']['people_with_leave']==2
        assert client.get(path+'&department=Finance',headers=admin).json()['summary']['people_with_leave']==1
        assert client.put('/api/workforce/leave-coverage/settings',headers=one,json={'warning_threshold':1}).status_code==403
        assert client.put('/api/workforce/leave-coverage/settings',headers=manager,json={'warning_threshold':1}).status_code==403
        assert client.put('/api/workforce/leave-coverage/settings',headers=admin,json={'warning_threshold':0}).status_code==422
        assert client.put('/api/workforce/leave-coverage/settings',headers=admin,json={'warning_threshold':1}).status_code==200
        assert client.get(path,headers=manager).json()['summary']['coverage_warning_days']>=1
        create={'title':'Quarterly employee review','guidance':'Document the review outcome','priority':'High','due_offset_days':7}
        assert client.post('/api/workforce/task-templates',headers=one,json=create).status_code==403
        assert client.post('/api/workforce/task-templates',headers=manager,json=create).status_code==403
        created=client.post('/api/workforce/task-templates',headers=admin,json=create)
        assert created.status_code==201,created.text
        tid=created.json()['id']
        assert client.post('/api/workforce/task-templates',headers=admin,json=create).status_code==409
        assert client.get('/api/workforce/task-templates',headers=one).status_code==403
        assert len(client.get('/api/workforce/task-templates',headers=manager).json())==1
        assert client.get('/api/workforce/task-templates?include_archived=true',headers=manager).status_code==403
        start_next=(date.today()+timedelta(days=1)).isoformat()
        payload={'employee_id':ids['TWO'],'start_date':start_next}
        assert client.post(f'/api/workforce/task-templates/{tid}/assign',headers=manager,json=payload).status_code==403
        payload['employee_id']=ids['OFF']
        assert client.post(f'/api/workforce/task-templates/{tid}/assign',headers=admin,json=payload).status_code==422
        payload['employee_id']=ids['ONE']
        created=client.post(f'/api/workforce/task-templates/{tid}/assign',headers=manager,json=payload)
        assert created.status_code==201,created.text
        assert created.json()['due_date']==(date.fromisoformat(start_next)+timedelta(days=7)).isoformat()
        assert client.post(f'/api/workforce/task-templates/{tid}/assign',headers=manager,json=payload).status_code==409
        assert client.post(f'/api/workforce/task-templates/{tid}/assign',headers=one,json=payload).status_code==403
        rows=client.get('/api/workforce/task-templates/assignments',headers=manager).json()
        assert len(rows)==1 and rows[0]['employee_id']==ids['ONE']
        assert client.get('/api/workforce/task-templates/assignments',headers=one).status_code==403
        assert client.patch(f'/api/workforce/task-templates/{tid}',headers=manager,json={'active':False}).status_code==403
        assert client.patch(f'/api/workforce/task-templates/{tid}',headers=admin,json={'active':False}).status_code==200
        assert len(client.get('/api/workforce/task-templates',headers=admin).json())==0
        assert len(client.get('/api/workforce/task-templates?include_archived=true',headers=admin).json())==1
        assert client.post(f'/api/workforce/task-templates/{tid}/assign',headers=admin,json={'employee_id':ids['TWO'],'start_date':start_next}).status_code==404
        with main.db() as c:
            assert c.execute('SELECT COUNT(*) AS n FROM hr_task_template_assignments').fetchone()['n']==1
            assert c.execute('SELECT COUNT(*) AS n FROM task_comments').fetchone()['n']==1
            assert c.execute("SELECT COUNT(*) AS n FROM audit_events WHERE action LIKE 'task.template.%'").fetchone()['n']>=3
            assert c.execute('SELECT COUNT(*) AS n FROM leave_coverage_settings').fetchone()['n']==1
    print('PASS: coverage visibility, private leave reasons, admin settings, active tasks, team scope, duplicate assignments, archive and audit')

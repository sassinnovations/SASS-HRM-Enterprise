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
        prefs='/api/workforce/leave-coverage/preferences'
        assert client.get(prefs).status_code==401
        default_prefs={'default_department':None,'show_holidays':True,'plan_status':'All','my_assignments_only':False}
        assert client.get(prefs,headers=one).json()==default_prefs
        assert client.put(prefs,headers=manager,json={'default_department':'Finance'}).status_code==403
        assert client.put(prefs,headers=admin,json={'default_department':'Retired dept'}).status_code==422
        assert client.put(prefs,headers=one,json={'plan_status':'Hidden'}).status_code==422
        manager_prefs={**default_prefs,'show_holidays':False,'plan_status':'Confirmed','my_assignments_only':True}
        assert client.put(prefs,headers=manager,json=manager_prefs).json()==manager_prefs
        admin_prefs={**default_prefs,'default_department':'Finance'}
        assert client.put(prefs,headers=admin,json=admin_prefs).json()==admin_prefs
        assert client.get(prefs,headers=admin).json()==admin_prefs
        assert client.get(prefs,headers=manager).json()==manager_prefs
        assert client.get(prefs,headers=one).json()==default_prefs
        assert client.put(prefs,headers=manager,json=default_prefs).json()==default_prefs
        saturday=start+timedelta(days=(5-start.weekday())%7)
        with main.db() as c:
            c.execute("""INSERT INTO leave_requests
              (employee_id,start_date,end_date,leave_type,reason,days,status,created_at)
              VALUES(?,?,?,?,?,1,'Approved',?)""",(ids['ONE'],saturday.isoformat(),saturday.isoformat(),
                    'Confidential category','Private details',start.isoformat()))
        def weekend_warning():
            return next(day for day in client.get(path,headers=manager).json()['days']
                        if day['day']==saturday.isoformat())
        assert weekend_warning()['coverage_warning']
        r=client.put('/api/workforce/leave-coverage/settings',headers=admin,
                     json={'warning_threshold':1,'weekdays_only':True})
        assert r.status_code==200 and r.json()['weekdays_only']
        assert not weekend_warning()['coverage_warning']
        assert weekend_warning()['on_leave'][0]['leave_type'] is None
        assert client.put('/api/workforce/leave-coverage/settings',headers=admin,
                          json={'warning_threshold':2}).json()['weekdays_only']
        plans='/api/workforce/leave-coverage/plans'
        payload={'label':'Payroll review backup','primary_employee_id':ids['ONE'],
                 'backup_employee_id':ids['MGR'],'status':'Planned','notes':'Managers-only handover',
                 'starts_on':(start-timedelta(days=1)).isoformat(),'ends_on':end.isoformat()}
        def visible_plans(headers,dept=''):
            return client.get(path+dept,headers=headers).json()['manual_plans']
        assert client.post(plans,headers=one,json=payload).status_code==403
        assert client.post(plans,headers=manager,json={**payload,'backup_employee_id':ids['TWO']}).status_code==403
        assert client.post(plans,headers=manager,json={**payload,'backup_employee_id':ids['OFF']}).status_code==403
        assert client.post(plans,headers=admin,json={**payload,'backup_employee_id':ids['ONE']}).status_code==422
        assert client.post(plans,headers=admin,json={**payload,'starts_on':end.isoformat(),'ends_on':start.isoformat()}).status_code==422
        assert client.post(plans,headers=admin,json={**payload,'label':'  '}).status_code==422
        created_plan=client.post(plans,headers=manager,json=payload)
        assert created_plan.status_code==201,created_plan.text
        plan_id=created_plan.json()['id']
        plan_path=f'{plans}/{plan_id}'
        assert visible_plans(manager)[0]['notes']==payload['notes']
        initial_plan=visible_plans(manager)[0]
        assert initial_plan['is_mine'] and not initial_plan['backup_on_leave']  # MGR only has pending leave.
        with main.db() as c:
            c.execute("""INSERT INTO leave_requests (employee_id,start_date,end_date,leave_type,reason,days,status,created_at)
                VALUES(?,?,?,?,?,1,'Approved',?)""",(ids['MGR'],end.isoformat(),end.isoformat(),
                 'Sensitive type','Private backup leave reason',start.isoformat()))
        warning_plan=visible_plans(manager)[0]
        assert warning_plan['backup_on_leave'] and 'Private backup leave reason' not in str(warning_plan)
        assert warning_plan['backup_leave_days']==[end.isoformat()]
        assert warning_plan['parallel_backup_days']==[]
        assert 'Sensitive type' not in str(warning_plan)
        assert visible_plans(admin)[0]['backup_on_leave'] and not visible_plans(admin)[0]['is_mine']
        assert visible_plans(admin,'&department=Engineering')[0]['id']==plan_id
        assert visible_plans(admin,'&department=Finance')==[]
        mine=visible_plans(one)
        assert len(mine)==1 and mine[0]['id']==plan_id and mine[0]['is_mine']
        assert not {'notes','backup_on_leave','backup_leave_days','parallel_backup_days'}.intersection(mine[0])
        assert visible_plans(two)==[]
        assert client.get(path,headers=one).json()['staff_choices']==[]
        assert {p['id'] for p in client.get(path,headers=manager).json()['staff_choices']}=={ids['MGR'],ids['ONE']}
        org_plan=client.post(plans,headers=admin,json={**payload,'primary_employee_id':ids['TWO']})
        assert org_plan.status_code==201,org_plan.text
        org_plan_path=f"{plans}/{org_plan.json()['id']}"
        assert len(visible_plans(manager))==1
        assert not visible_plans(manager)[0]['parallel_backup_days']  # Cross-team plan is hidden from MGR.
        assert visible_plans(admin,'&department=Engineering')[0]['parallel_backup_days']==[
            start.isoformat(),end.isoformat()]  # HR can review a conflict across departments.
        sibling=client.post(plans,headers=manager,json={**payload,'label':'Another handover',
                            'starts_on':end.isoformat(),'ends_on':end.isoformat()})
        assert sibling.status_code==201,sibling.text
        scoped=visible_plans(manager)
        assert len(scoped)==2 and all(row['parallel_backup_days']==[end.isoformat()] for row in scoped)
        sibling_path=f"{plans}/{sibling.json()['id']}"
        assert client.request('DELETE',sibling_path,headers=manager,json={'confirm':'DELETE','revision':1}).status_code==200
        assert not visible_plans(manager)[0]['parallel_backup_days']
        assert client.put(org_plan_path,headers=manager,json={**payload,'revision':1}).status_code==404
        assert client.request('DELETE',org_plan_path,headers=manager,json={'confirm':'DELETE','revision':1}).status_code==404
        assert client.put(plan_path,headers=one,json={**payload,'revision':1}).status_code==403
        revised={**payload,'label':'Updated backup plan','status':'Confirmed','revision':1}
        r=client.put(plan_path,headers=manager,json=revised)
        assert r.status_code==200 and r.json()['revision']==2,r.text
        assert visible_plans(one)[0]['status']=='Confirmed'
        assert client.put(plan_path,headers=manager,json=revised).status_code==409
        assert client.request('DELETE',plan_path,headers=manager,json={'confirm':'DELETE','revision':1}).status_code==409
        assert client.request('DELETE',plan_path,headers=manager,json={'confirm':'NO','revision':2}).status_code==422
        assert client.request('DELETE',plan_path,headers=manager,json={'confirm':'DELETE','revision':2}).status_code==200
        assert visible_plans(one)==[] and visible_plans(manager)==[]
        assert client.request('DELETE',plan_path,headers=manager,json={'confirm':'DELETE','revision':2}).status_code==404
        with main.db() as c:
            assert c.execute('SELECT deleted_at FROM leave_coverage_manual_plans WHERE id=?',(plan_id,)).fetchone()['deleted_at']
            assert c.execute("SELECT COUNT(*) AS n FROM audit_events WHERE target=? AND action LIKE 'leave.coverage.plan.%'",
                             (f'leave_coverage_plan:{plan_id}',)).fetchone()['n']==3
            assert c.execute('SELECT COUNT(*) AS n FROM leave_requests').fetchone()['n']==6
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
    print('PASS: coverage visibility, manual plans, per-account settings, exact-day and parallel backup warnings, permission boundaries, leave privacy, concurrency, audit, task templates')

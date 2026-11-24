"""v3.8 regression: administrator-only data quality scan, review, configuration and safe export."""
import os
import tempfile
from pathlib import Path
from datetime import date, timedelta

from fastapi.testclient import TestClient
os.environ.update(SASS_HRM_TESTING='1',DB_ENGINE='sqlite',
                  JWT_SECRET='test-v38-hr-quality-isolated-secret-0123456789-ABCDE')
with tempfile.TemporaryDirectory() as d:
    os.environ['DATABASE_PATH']=str(Path(d)/'test.sqlite')
    import main
    with TestClient(main.app) as client:
        past=(date.today()-timedelta(days=20)).isoformat()
        future=(date.today()+timedelta(days=10)).isoformat()
        with main.db() as c:
            user_ids={}
            for name,role,dept in [('Boss','admin','HR'),('Other','admin','HR'),('Manager','manager','Sales'),('Worker','employee',''),('Idle','employee','Tech')]:
                r=c.execute('''INSERT INTO employees(code,name,email,role,designation,department,
                  location,join_date,password_hash,account_active) VALUES(?,?,?,?,?,?,?,?,?,1)''',
                  (name.upper(),name,name.lower()+'@example.invalid',role,'Analyst',dept,'Pune',past,main.hash_password('Test-only-password-123')))
                user_ids[name]=r.lastrowid
            c.execute('UPDATE employees SET manager_id=? WHERE id=?',(user_ids['Idle'],user_ids['Worker']))
            c.execute('UPDATE employees SET account_active=0 WHERE id=?',(user_ids['Idle'],))
            c.execute('INSERT INTO onboarding(employee_id,title,due_date,status) VALUES(?,?,?,?)',
                      (user_ids['Worker'],'Complete employee induction',past,'Pending'))
            c.execute('INSERT INTO hr_tasks(title,assignee_id,created_by,due_date,status,created_at) VALUES(?,?,?,?,?,?)',
                      ('=DANGEROUS_FORMULA()',user_ids['Worker'],user_ids['Boss'],past,'Open',past))
            c.execute('INSERT INTO hr_tasks(title,assignee_id,created_by,due_date,status,created_at) VALUES(?,?,?,?,?,?)',
                      ('Future task',user_ids['Worker'],user_ids['Boss'],future,'Open',past))
            c.execute('INSERT INTO leave_requests(employee_id,start_date,end_date,leave_type,reason,days,status,created_at) VALUES(?,?,?,?,?,?,?,?)',
                      (user_ids['Worker'],future,future,'Personal leave','private medical explanation must never appear',1,'Pending',past))
            c.execute('INSERT INTO tickets(employee_id,subject,category,description,status,created_at) VALUES(?,?,?,?,?,?)',
                      (user_ids['Worker'],'General help','Other','PRIVATE helpdesk message must not appear','Open',past))
        def auth(who):
            result=client.post('/api/auth/login',json={'email':who.lower()+'@example.invalid','password':'Test-only-password-123'})
            assert result.status_code==200,result.text
            return {'Authorization':'Bearer '+result.json()['token']}
        boss=auth('Boss');other=auth('Other');manager=auth('Manager');worker=auth('Worker')
        base='/api/admin/data-quality'
        for path in ('/issues','/policy','/export.csv'):
            assert client.get(base+path).status_code==401
            for h in (worker,manager):
                assert client.get(base+path,headers=h).status_code==403
        assert client.put(base+'/policy',headers=manager,json={'task_grace_days':0,'onboarding_grace_days':0,'leave_review_days':7,'helpdesk_review_days':14}).status_code==403
        r=client.get(base+'/issues',headers=boss)
        assert r.status_code==200,r.text
        items=r.json()['items']
        keys={x['key'] for x in items}
        assert {f'employee_profile:{user_ids["Worker"]}',f'manager_relationship:{user_ids["Worker"]}',
                'onboarding_overdue:1','task_overdue:1','leave_review_delay:1','helpdesk_review_delay:1'} <=keys,keys
        assert 'task_overdue:2' not in keys
        assert 'private medical' not in r.text and 'PRIVATE helpdesk' not in r.text
        assert all('reason' not in item and 'password_hash' not in item for item in items)
        assert client.get(base+'/issues',params={'kind':'injected'},headers=boss).status_code==422
        assert client.get(base+'/issues',params={'status':'Fake'},headers=boss).status_code==422
        assert client.get(base+'/issues',params={'limit':0},headers=boss).status_code==422
        assert client.get(base+'/issues',params={'kind':'task_overdue','status':'Open'},headers=boss).json()['total']==1
        assert client.get(base+'/issues',params={'q':'induction'},headers=boss).json()['total']==1
        assert client.put(base+'/policy',headers=boss,json={'task_grace_days':-1,'onboarding_grace_days':0,'leave_review_days':7,'helpdesk_review_days':14}).status_code==422
        assert client.put(base+'/policy',headers=boss,json={'task_grace_days':0,'onboarding_grace_days':0,'leave_review_days':0,'helpdesk_review_days':14}).status_code==422
        policy=client.put(base+'/policy',headers=boss,json={'task_grace_days':3,'onboarding_grace_days':1,'leave_review_days':6,'helpdesk_review_days':10})
        assert policy.status_code==200,policy.text
        assert client.get(base+'/policy',headers=other).json()['leave_review_days']==6
        issue=f'employee_profile/{user_ids["Worker"]}'
        assert client.put(base+f'/issues/{issue}/review',headers=worker,json={'status':'Reviewed'}).status_code==403
        assert client.put(base+f'/issues/{issue}/review',headers=boss,json={'status':'Reviewed','assigned_to':user_ids['Manager']}).status_code==422
        assert client.put(base+f'/issues/{issue}/review',headers=boss,json={'status':'Reviewed','assigned_to':user_ids['Idle']}).status_code==422
        reviewed=client.put(base+f'/issues/{issue}/review',headers=boss,json={'status':'In progress','assigned_to':user_ids['Other'],'note':'Check department data'})
        assert reviewed.status_code==200,reviewed.text
        assert client.put(base+f'/issues/{issue}/review',headers=boss,json={'status':'Reviewed','note':'HR reviewed'}).status_code==200
        assert client.get(base+'/issues',params={'status':'Reviewed'},headers=other).json()['total']==1
        assert client.put(base+'/issues/task_overdue/2/review',headers=boss,json={'status':'Reviewed'}).status_code==404
        with main.db() as c:
            assert c.execute('SELECT COUNT(*) FROM hr_data_quality_reviews').fetchone()[0]==1
            assert c.execute('SELECT COUNT(*) FROM audit_events WHERE action LIKE ?',('quality.%',)).fetchone()[0]>=3
            c.execute('UPDATE employees SET department=? WHERE id=?',('Engineering',user_ids['Worker']))
        assert client.get(base+'/issues',params={'status':'Reviewed'},headers=boss).json()['total']==0
        csv_out=client.get(base+'/export.csv',headers=boss)
        assert csv_out.status_code==200,csv_out.text
        assert "'=DANGEROUS_FORMULA()" in csv_out.text
        assert 'private medical' not in csv_out.text and 'PRIVATE helpdesk' not in csv_out.text
        assert client.get(base+'/export.csv',params={'kind':'random'},headers=boss).status_code==422
    print('PASS v3.8: HR-only access, 6 rules, validation, review persistence, assignment, source resolution, audit trail and safe CSV')

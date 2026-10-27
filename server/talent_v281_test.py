"""v2.8.1 account scoped edits and regression checks using a disposable SQLite database.
Run: python talent_v281_test.py (never points at a real employee database).
"""
import os
import tempfile
from datetime import date, timedelta
from pathlib import Path
os.environ.update(SASS_HRM_TESTING='1', DB_ENGINE='sqlite', JWT_SECRET='integration-test-only-random-jwt-secret-12345678901234567890')
from fastapi.testclient import TestClient

with tempfile.TemporaryDirectory() as d:
    os.environ['DATABASE_PATH'] = str(Path(d) / 'isolated.db')
    import main
    with TestClient(main.app) as client:
        with main.db() as c:
            people = [
                ('HR1', 'HR Administrator', 'hr@sass.invalid', 'admin', None),
                ('MG1', 'Task Manager', 'manager@sass.invalid', 'manager', None),
                ('EM1', 'Team Member', 'member@sass.invalid', 'employee', 2),
                ('MG2', 'Other Manager', 'other@sass.invalid', 'manager', None),
            ]
            for code, name, email, role, mgr in people:
                c.execute('''INSERT INTO employees(code,name,email,role,designation,department,location,join_date,manager_id,password_hash,account_active)
                             VALUES(?,?,?,?,?,?,?,?,?,?,1)''',
                          (code,name,email,role,'Staff','People','Head Office','2026-01-01',mgr,main.hash_password('TestPassword123!')))
        auth = {}
        for role,email in [('hr','hr@sass.invalid'),('mgr','manager@sass.invalid'),('mem','member@sass.invalid'),('other','other@sass.invalid')]:
            r = client.post('/api/auth/login',json={'email':email,'password':'TestPassword123!'})
            assert r.status_code==200,r.text
            auth[role]={'Authorization':'Bearer '+r.json()['token']}
        def post(role, path, body): return client.post('/api'+path,headers=auth[role],json=body)
        def patch(role, path, body): return client.patch('/api'+path,headers=auth[role],json=body)
        def get(role, path): return client.get('/api'+path,headers=auth[role])
        cand=post('mgr','/candidates',{'name':'Test Candidate','job_title':'Analyst','source':'Referral'})
        assert cand.status_code==201,cand.text
        cid=cand.json()['id']
        detail={'name':'Updated Candidate','job_title':'Data Analyst','source':'Career site'}
        assert patch('mem',f'/talent/candidates/{cid}/details',detail).status_code==403
        assert patch('mgr',f'/talent/candidates/{cid}/details',detail).status_code==200
        assert get('hr','/candidates').json()[0]['job_title']=='Data Analyst'
        assert patch('mgr',f'/talent/candidates/{cid}/details',{**detail,'name':''}).status_code==422
        assert patch('hr','/talent/candidates/999999/details',detail).status_code==404
        template=post('hr','/talent/onboarding/templates',{'title':'Security induction','offset_days':3})
        assert template.status_code==201,template.text
        tid=template.json()['id']
        edited={'title':'Security orientation','offset_days':4,'active':True}
        assert patch('mem',f'/talent/onboarding/templates/{tid}',edited).status_code==403
        assert patch('mgr',f'/talent/onboarding/templates/{tid}',edited).status_code==403
        assert patch('hr',f'/talent/onboarding/templates/{tid}',edited).status_code==200
        assert get('mem','/talent/onboarding/templates').json()[0]['title']=='Security orientation'
        assert patch('hr',f'/talent/onboarding/templates/{tid}',{**edited,'active':False}).status_code==200
        assert get('hr','/talent/onboarding/templates').json()==[]
        assert get('mem','/talent/onboarding/templates?include_archived=true').status_code==403
        assert len(get('hr','/talent/onboarding/templates?include_archived=true').json())==1
        start=date.today().isoformat()
        assert post('hr',f'/talent/onboarding/templates/{tid}/assign',{'employee_id':3,'start_date':start}).status_code==409
        due=(date.today()+timedelta(days=10)).isoformat()
        task=post('mgr','/tasks',{'title':'Prepare team audit','assignee_id':3,'due_date':due,'priority':'Normal'})
        assert task.status_code==201,task.text
        task_id=task.json()['id']
        task_edit={'title':'Prepare monthly team audit','due_date':due,'priority':'High'}
        assert patch('mem',f'/talent/tasks/{task_id}/details',task_edit).status_code==403
        assert patch('other',f'/talent/tasks/{task_id}/details',task_edit).status_code==403
        assert patch('mgr',f'/talent/tasks/{task_id}/details',task_edit).status_code==200
        assert get('mgr','/tasks').json()[0]['priority']=='High'
        assert patch('hr',f'/talent/tasks/{task_id}/details',{**task_edit,'priority':'Low'}).status_code==200
        assert patch('mgr',f'/talent/tasks/{task_id}/details',{**task_edit,'due_date':'2020-01-01'}).status_code==422
        assert patch('mem',f'/tasks/{task_id}',{'status':'Completed'}).status_code==200
        assert patch('mgr',f'/talent/tasks/{task_id}/details',task_edit).status_code==409
        audit=get('hr','/audit')
        assert audit.status_code==200
        assert any(a['action']=='onboarding.template.updated' for a in audit.json())
        assert any(a['action']=='talent.task.details.updated' for a in audit.json())
        print('PASS v2.8.1: candidate edits, template archive/assign safety, task ownership, audit, validation')

"""Isolated workflow and authorization tests: SQLite is test-only; no external records."""
import os, tempfile
from datetime import date,datetime,timedelta,timezone
from pathlib import Path
os.environ.update(SASS_HRM_TESTING='1',DB_ENGINE='sqlite',JWT_SECRET='talent-ops-integration-testing-secret-1234567890')
from fastapi.testclient import TestClient
with tempfile.TemporaryDirectory() as directory:
    os.environ['DATABASE_PATH']=str(Path(directory)/'tests.db')
    import main
    with TestClient(main.app) as client:
        with main.db() as c:
            people=[('HR1','HR Manager','admin@sass.invalid','admin',None),('MG1','Manager','manager@sass.invalid','manager',None),('E01','First Employee','e1@sass.invalid','employee',2),('E02','Second Employee','e2@sass.invalid','employee',None)]
            for code,name,email,role,manager in people:
                c.execute('''INSERT INTO employees(code,name,email,role,designation,department,location,join_date,manager_id,password_hash,account_active)
                    VALUES(?,?,?,?,?,?,?,?,?,?,1)''',(code,name,email,role,'Staff','People','Chennai','2026-01-01',manager,main.hash_password('LongTestPassword134!')))
        auth={}
        for role,email in [('hr','admin@sass.invalid'),('manager','manager@sass.invalid'),('one','e1@sass.invalid'),('two','e2@sass.invalid')]:
            result=client.post('/api/auth/login',json={'email':email,'password':'LongTestPassword134!'})
            assert result.status_code==200,result.text
            auth[role]={'Authorization':'Bearer '+result.json()['token']}
        def get(r,p):return client.get('/api'+p,headers=auth[r])
        def post(r,p,data):return client.post('/api'+p,json=data,headers=auth[r])
        def patch(r,p,data):return client.patch('/api'+p,json=data,headers=auth[r])
        # Candidate recruiter notes exclude employees and audit logs don't disclose the note content.
        candidate=post('hr','/candidates',{'name':'Synthetic Candidate','job_title':'Engineer','source':'Referral'})
        assert candidate.status_code==201,candidate.text
        candidate_id=candidate.json()['id']
        note='Confidential interviewer planning note that should not appear in an audit log'
        assert post('one',f'/talent/candidates/{candidate_id}/activity',{'note':note}).status_code==403
        assert post('manager',f'/talent/candidates/{candidate_id}/activity',{'note':note}).status_code==201
        assert len(get('hr',f'/talent/candidates/{candidate_id}/activity').json())==1
        assert get('one',f'/talent/candidates/{candidate_id}/activity').status_code==403
        assert note not in str(get('hr','/audit').json())
        assert get('hr','/talent/candidates/50000/activity').status_code==404
        # Reusable onboarding templates and idempotent task assignment.
        assert get('one','/talent/onboarding/templates').status_code==200
        assert post('one','/talent/onboarding/templates',{'title':'Verify legal work authorization','offset_days':1}).status_code==403
        t=post('hr','/talent/onboarding/templates',{'title':'Verify legal work authorization','offset_days':2})
        assert t.status_code==201,t.text
        tid=t.json()['id']
        assert post('hr','/talent/onboarding/templates',{'title':'Verify legal work authorization','offset_days':2}).status_code==409
        due=(date.today()+timedelta(days=6)).isoformat()
        start=(date.today()+timedelta(days=4)).isoformat()
        task=post('hr',f'/talent/onboarding/templates/{tid}/assign',{'employee_id':3,'start_date':start})
        assert task.status_code==201,task.text
        assert task.json()['due_date']==due
        assert post('hr',f'/talent/onboarding/templates/{tid}/assign',{'employee_id':3,'start_date':start}).status_code==409
        assert len(get('one','/onboarding').json())==1
        assert get('two','/onboarding').json()==[]
        # Ticket ownership restricted to HR; target due date cannot be in past.
        ticket=post('one','/helpdesk/tickets',{'subject':'Badge access issue','description':'Cannot enter the office','category':'Facilities'})
        assert ticket.status_code==201,ticket.text
        ticket_id=ticket.json()['id']
        assert get('manager','/talent/helpdesk/queue').status_code==403
        assert get('one','/talent/helpdesk/queue').status_code==403
        assert post('manager',f'/talent/helpdesk/{ticket_id}/triage',{'assignee_id':1,'due_date':due}).status_code==403
        assert post('hr',f'/talent/helpdesk/{ticket_id}/triage',{'assignee_id':3,'due_date':due}).status_code==422
        assert post('hr',f'/talent/helpdesk/{ticket_id}/triage',{'assignee_id':1,'due_date':'2020-01-01'}).status_code==422
        assert post('hr',f'/talent/helpdesk/{ticket_id}/triage',{'assignee_id':1,'due_date':due}).status_code==200
        q=get('hr','/talent/helpdesk/queue').json()
        assert q[0]['assignee_id']==1 and q[0]['due_date']==due
        # Managers cannot read offboarding checklists unless the employee is themselves.
        off=post('one','/offboarding',{'last_working_day':date.today().isoformat(),'reason':'Career transition'})
        assert off.status_code==201,off.text
        oid=off.json()['id']
        assert get('manager',f'/talent/offboarding/{oid}/clearance').status_code==403
        assert post('one',f'/talent/offboarding/{oid}/clearance',{'title':'Return badge'}).status_code==403
        assert patch('hr',f'/offboarding/{oid}',{'status':'Closed'}).status_code==409
        assert patch('hr',f'/offboarding/{oid}',{'status':'Under Review'}).status_code==200
        clear=post('hr',f'/talent/offboarding/{oid}/clearance',{'title':'Return badge'})
        assert clear.status_code==201,clear.text
        assert post('hr',f'/talent/offboarding/{oid}/clearance',{'title':'Return badge'}).status_code==409
        assert len(get('one',f'/talent/offboarding/{oid}/clearance').json())==1
        assert get('two',f'/talent/offboarding/{oid}/clearance').status_code==403
        assert patch('hr',f'/offboarding/{oid}',{'status':'Approved'}).status_code==200
        assert patch('hr',f'/offboarding/{oid}',{'status':'Closed'}).status_code==409
        cid=clear.json()['id']
        assert patch('hr',f'/talent/offboarding/clearance/{cid}',{'status':'Completed'}).status_code==200
        assert patch('hr',f'/offboarding/{oid}',{'status':'Closed'}).status_code==200
        assert patch('hr',f'/talent/offboarding/clearance/{cid}',{'status':'Pending'}).status_code==409
        # Task comments honor owner + creator scope.
        hr_task=post('manager','/tasks',{'title':'Prepare monthly summary','assignee_id':3,'due_date':due})
        assert hr_task.status_code==201,hr_task.text
        task_id=hr_task.json()['id']
        assert get('two',f'/talent/tasks/{task_id}/comments').status_code==403
        assert post('two',f'/talent/tasks/{task_id}/comments',{'message':'No access'}).status_code==403
        assert post('one',f'/talent/tasks/{task_id}/comments',{'message':'I will prepare this by Friday'}).status_code==201
        assert len(get('manager',f'/talent/tasks/{task_id}/comments').json())==1
        # Request Desk conversations expose messages only to the owner and HR.
        cat=post('hr','/request-desk/categories',{'name':'Employment certificate','description':'Issued by HR after approval'})
        assert cat.status_code==201,cat.text
        srv=post('one','/request-desk/requests',{'category_id':cat.json()['id'],'subject':'Work certificate','details':'Please provide employment confirmation.'})
        assert srv.status_code==201,srv.text
        sid=srv.json()['id']
        assert get('manager',f'/talent/request-desk/{sid}/messages').status_code==403
        assert post('two',f'/talent/request-desk/{sid}/messages',{'message':'I am not the owner'}).status_code==403
        assert post('one',f'/talent/request-desk/{sid}/messages',{'message':'Needed this week'}).status_code==201
        assert post('hr',f'/talent/request-desk/{sid}/messages',{'message':'We are preparing it'}).status_code==201
        assert len(get('one',f'/talent/request-desk/{sid}/messages').json())==2
        assert post('hr',f'/request-desk/requests/{sid}/decision',{'status':'In Progress'}).status_code==200
        assert post('hr',f'/request-desk/requests/{sid}/decision',{'status':'Fulfilled','hr_response':'Certificate ready at reception.'}).status_code==200
        assert post('one',f'/talent/request-desk/{sid}/messages',{'message':'Further comment'}).status_code==409
        # Interview overlap is rejected even for timezone-equivalent timestamps.
        first=(datetime.now(timezone.utc)+timedelta(days=3)).replace(microsecond=0)
        first_interview=post('manager','/recruitment/interviews',{'candidate_id':candidate_id,'interviewer_id':2,'scheduled_at':first.isoformat(),'duration_minutes':60,'mode':'Video'})
        assert first_interview.status_code==201,first_interview.text
        overlap=post('manager','/recruitment/interviews',{'candidate_id':candidate_id,'interviewer_id':2,'scheduled_at':(first+timedelta(minutes=30)).isoformat(),'duration_minutes':45,'mode':'Phone'})
        assert overlap.status_code==409,overlap.text
        non_overlap=post('manager','/recruitment/interviews',{'candidate_id':candidate_id,'interviewer_id':2,'scheduled_at':(first+timedelta(minutes=60)).isoformat(),'duration_minutes':45,'mode':'Video'})
        assert non_overlap.status_code==201,non_overlap.text
        print('PASS Talent ops: recruiter notes, templates, support triage, exit clearance, task comments, service privacy, interviewer conflicts')

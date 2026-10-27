"""Isolated integration tests for human-led culture and service workflows (never MySQL production)."""
import os, tempfile
from pathlib import Path
os.environ.update(SASS_HRM_TESTING='1', DB_ENGINE='sqlite', JWT_SECRET='culture-workflow-testing-random-secret-1234567890-abcdef12345')
from fastapi.testclient import TestClient
with tempfile.TemporaryDirectory() as d:
    os.environ['DATABASE_PATH']=str(Path(d)/'culture.db')
    import main
    with TestClient(main.app) as client:
        with main.db() as conn:
            people=[('SASS-A','SASS HR Admin','hr@sass.invalid','admin',None),
                    ('SASS-M','SASS Team Lead','lead@sass.invalid','manager',None),
                    ('SASS-E1','SASS First Employee','staff1@sass.invalid','employee',2),
                    ('SASS-E2','SASS Second Employee','staff2@sass.invalid','employee',None)]
            for code,name,email,role,manager in people:
                conn.execute('''INSERT INTO employees(code,name,email,role,designation,department,location,join_date,
                    manager_id,password_hash,account_active) VALUES(?,?,?,?,?,?,?,?,?,?,1)''',
                    (code,name,email,role,'Staff','Engineering','Chennai','2026-01-01',manager,main.hash_password('TestCulturePassword123!')))
        headers={}
        for k,e in [('admin','hr@sass.invalid'),('manager','lead@sass.invalid'),('one','staff1@sass.invalid'),('two','staff2@sass.invalid')]:
            r=client.post('/api/auth/login',json={'email':e,'password':'TestCulturePassword123!'})
            assert r.status_code==200,(k,r.text)
            headers[k]={'Authorization':'Bearer '+r.json()['token']}
        def get(k,p):return client.get('/api'+p,headers=headers[k])
        def post(k,p,data):return client.post('/api'+p,json=data,headers=headers[k])
        def patch(k,p,data):return client.patch('/api'+p,json=data,headers=headers[k])
        for p in ['/career/plans','/voice/cases','/discipline/cases','/request-desk/categories','/request-desk/requests']:
            assert get('one',p).status_code==200,p
            assert get('one',p).json()==[],p
        assert get('one','/career/plans').status_code==200
        # Career plan ownership, team visibility, milestones and notes.
        plan=post('one','/career/plans',{'target_role':'Technical Lead','aspiration':'Develop project leadership and architecture skills','target_date':'2027-06-01'})
        assert plan.status_code==201,plan.text
        pid=plan.json()['id']
        assert len(get('manager','/career/plans').json())==1
        assert get('two','/career/plans').json()==[]
        assert post('two',f'/career/plans/{pid}/milestones',{'title':'Not allowed','due_date':'2027-01-01'}).status_code==403
        assert post('one',f'/career/plans/{pid}/milestones',{'title':'Complete mentoring','due_date':'2027-01-01'}).status_code==201
        m=get('one',f'/career/plans/{pid}/milestones').json()[0]
        assert patch('one',f'/career/milestones/{m["id"]}',{'status':'Completed'}).status_code==200
        assert patch('one',f'/career/plans/{pid}',{'status':'Completed','progress':60}).status_code==422
        assert patch('one',f'/career/plans/{pid}',{'status':'In Progress','progress':45,'manager_note':'Fake manager review'}).status_code==403
        assert patch('manager',f'/career/plans/{pid}',{'status':'In Progress','progress':45,'manager_note':'Good progress'}).status_code==200
        assert patch('two',f'/career/plans/{pid}',{'status':'Completed','progress':100}).status_code==403
        # Employee Voice is restricted to the reporter and HR, not managers or other employees.
        voice=post('one','/voice/cases',{'category':'Workplace concern','title':'Test employee relations concern','description':'This is a synthetic test-only workplace concern.'})
        assert voice.status_code==201,voice.text
        vid=voice.json()['id']
        assert len(get('manager','/voice/cases').json())==0
        assert get('manager',f'/voice/cases/{vid}/messages').status_code==403
        assert get('two',f'/voice/cases/{vid}/messages').status_code==403
        assert post('one',f'/voice/cases/{vid}/messages',{'message':'Please review my report.'}).status_code==201
        assert post('manager',f'/voice/cases/{vid}/decision',{'status':'In Review'}).status_code==403
        assert post('admin',f'/voice/cases/{vid}/decision',{'status':'Resolved','resolution_note':'Reviewed'}).status_code==409
        assert post('admin',f'/voice/cases/{vid}/decision',{'status':'In Review'}).status_code==200
        assert post('admin',f'/voice/cases/{vid}/decision',{'status':'Resolved','resolution_note':'Reviewed by HR team'}).status_code==200
        assert get('two','/voice/cases').json()==[]
        # Discipline is HR-only at draft stage, visible to affected employee after notice.
        discipline=post('admin','/discipline/cases',{'employee_id':3,'category':'Policy concern','summary':'Synthetic policy training issue for test purposes','incident_date':'2026-10-01'})
        assert discipline.status_code==201,discipline.text
        did=discipline.json()['id']
        assert get('one','/discipline/cases').json()==[]
        assert get('manager','/discipline/cases').json()==[]
        assert post('manager','/discipline/cases',{'employee_id':4,'category':'Conduct','summary':'Synthetic test record only','incident_date':'2026-10-01'}).status_code==403
        assert post('admin',f'/discipline/cases/{did}/status',{'status':'Notified'}).status_code==200
        assert len(get('one','/discipline/cases').json())==1
        assert get('two','/discipline/cases').json()==[]
        assert post('two',f'/discipline/cases/{did}/response',{'response':'Cannot respond for someone else'}).status_code==403
        assert post('one',f'/discipline/cases/{did}/response',{'response':'The case needs further review.'}).status_code==200
        assert len(get('one',f'/discipline/cases/{did}/responses').json())==1
        assert get('two',f'/discipline/cases/{did}/responses').status_code==403
        assert post('admin',f'/discipline/cases/{did}/status',{'status':'Under Review'}).status_code==200
        assert post('admin',f'/discipline/cases/{did}/status',{'status':'Resolved','outcome':'Human-reviewed outcome for training only.'}).status_code==200
        assert post('one',f'/discipline/cases/{did}/response',{'response':'Late response'}).status_code==409
        # Request catalog starts empty; HR can create; owner and HR can view own work.
        assert post('one','/request-desk/categories',{'name':'Employment letter'}).status_code==403
        cat=post('admin','/request-desk/categories',{'name':'Employment letter','description':'Request an employment letter'})
        assert cat.status_code==201,cat.text
        cid=cat.json()['id']
        request=post('one','/request-desk/requests',{'category_id':cid,'subject':'Employment verification','details':'Please prepare my current employment letter.'})
        assert request.status_code==201,request.text
        rid=request.json()['id']
        assert get('manager','/request-desk/requests').json()==[]
        assert get('two','/request-desk/requests').json()==[]
        assert post('manager',f'/request-desk/requests/{rid}/decision',{'status':'In Progress'}).status_code==403
        assert post('admin',f'/request-desk/requests/{rid}/decision',{'status':'Fulfilled','hr_response':'Completed'}).status_code==409
        assert post('admin',f'/request-desk/requests/{rid}/decision',{'status':'In Progress'}).status_code==200
        assert post('admin',f'/request-desk/requests/{rid}/decision',{'status':'Fulfilled','hr_response':'Letter prepared for collection.'}).status_code==200
        assert len(get('one','/request-desk/requests').json())==1
        # AI assistance cannot retrieve another person's private career/service data.
        ai_one=post('one','/ai/chat',{'message':'Show my career plan'})
        ai_two=post('two','/ai/chat',{'message':'Show my career plan'})
        assert ai_one.status_code==200 and 'Technical Lead' in ai_one.json()['answer']
        assert ai_two.status_code==200 and 'do not have a career plan' in ai_two.json()['answer']
        assert 'Employment verification' in post('one','/ai/chat',{'message':'What is my service request status?'}).json()['answer']
        guidance=post('one','/ai/chat',{'message':'How do I submit an Employee Voice concern?'})
        assert guidance.status_code==200 and guidance.json()['mode']=='navigation'
        # Sensitive descriptions never appear in global audit details.
        assert 'synthetic test-only workplace concern' not in str(get('admin','/audit').json())
        print('PASS culture suite: career visibility/milestones, confidential voice, fair-process discipline, HR service catalog + statuses')

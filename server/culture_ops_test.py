"""Culture v1.9 workflow regression: isolated fictional accounts and SQLite only."""
import os, tempfile
from pathlib import Path
os.environ.update(SASS_HRM_TESTING='1',DB_ENGINE='sqlite',JWT_SECRET='culture-v19-test-secret-key-at-least-32-chars-12453')
from fastapi.testclient import TestClient
with tempfile.TemporaryDirectory() as d:
    os.environ['DATABASE_PATH']=str(Path(d)/'culture_ops.db')
    import main
    with TestClient(main.app) as app:
        with main.db() as c:
            accounts=[('ROOT','HR User','admin@example.invalid','admin',None),
                      ('MGR','Team Manager','manager@example.invalid','manager',None),
                      ('EMP1','First Employee','first@example.invalid','employee',2),
                      ('EMP2','Second Employee','second@example.invalid','employee',None),
                      ('EMP3','Third Employee','third@example.invalid','employee',None)]
            for code,name,email,role,manager in accounts:
                c.execute('''INSERT INTO employees(code,name,email,role,designation,department,location,join_date,manager_id,password_hash,account_active)
                        VALUES(?,?,?,?,?,?,?,?,?,?,1)''',(code,name,email,role,'Associate','Engineering','Chennai','2026-01-01',manager,main.hash_password('SyntheticOnlyPassw0rd!')))
        hdr={}
        for who,email in [('admin','admin@example.invalid'),('manager','manager@example.invalid'),('one','first@example.invalid'),('two','second@example.invalid'),('three','third@example.invalid')]:
            reply=app.post('/api/auth/login',json={'email':email,'password':'SyntheticOnlyPassw0rd!'})
            assert reply.status_code==200,reply.text
            hdr[who]={'Authorization':'Bearer '+reply.json()['token']}
        def post(w,path,body=None):return app.post('/api'+path,json=body,headers=hdr[w])
        def get(w,path):return app.get('/api'+path,headers=hdr[w])
        def patch(w,path,body):return app.patch('/api'+path,json=body,headers=hdr[w])
        # Performance: history created only by successful changes; manager may edit direct report.
        result=post('one','/performance/goals',{'employee_id':3,'title':'Complete architecture practice','description':'Learning modules','due_date':'2027-05-01'})
        assert result.status_code==201,result.text
        goal=result.json()['id']
        assert get('two',f'/culture/goals/{goal}/history').status_code==403
        assert patch('two',f'/performance/goals/{goal}',{'progress':20}).status_code==403
        assert patch('manager',f'/performance/goals/{goal}',{'progress':40,'note':'Reviewed skills progress'}).status_code==200
        assert patch('manager',f'/performance/goals/{goal}',{'progress':40}).status_code==409
        assert patch('one',f'/performance/goals/{goal}',{'progress':75,'note':'Completed new learning modules'}).status_code==200
        history=get('one',f'/culture/goals/{goal}/history')
        assert history.status_code==200 and len(history.json())==2
        assert history.json()[0]['old_progress']==40 and history.json()[0]['new_progress']==75
        assert get('manager',f'/culture/goals/{goal}/history').status_code==200
        # Career plans with milestones cannot be closed early.
        career=post('one','/career/plans',{'target_role':'Engineering Lead','aspiration':'Complete a year of leadership mentoring','target_date':'2027-12-31'})
        assert career.status_code==201,career.text
        cid=career.json()['id']
        step=post('one',f'/career/plans/{cid}/milestones',{'title':'Complete mentoring','due_date':'2027-08-01'})
        assert step.status_code==201,step.text
        assert patch('one',f'/career/plans/{cid}',{'status':'Completed','progress':100}).status_code==409
        assert patch('one',f'/career/milestones/{step.json()["id"]}',{'status':'Completed'}).status_code==200
        assert patch('one',f'/career/plans/{cid}',{'status':'Completed','progress':100}).status_code==200
        # Training: employee can request evidence review only on own completed course.
        course=post('admin','/training/courses',{'title':'Advanced workplace safety','category':'Compliance','duration_hours':4,'description':'Training course'})
        assert course.status_code==201,course.text
        eid=post('one','/training/enrollments',{'course_id':course.json()['id']})
        assert eid.status_code==201,eid.text
        enid=eid.json()['id']
        assert post('one','/culture/training/verifications',{'enrollment_id':enid,'evidence_note':'Completed course assessments successfully'}).status_code==409
        assert patch('one',f'/training/enrollments/{enid}',{'status':'Completed'}).status_code==200
        assert post('two','/culture/training/verifications',{'enrollment_id':enid,'evidence_note':'Trying to verify somebody else'}).status_code==403
        r=post('one','/culture/training/verifications',{'enrollment_id':enid,'evidence_note':'Completed the course and passed the final assessment.'})
        assert r.status_code==201,r.text
        ident=r.json()['id']
        assert get('two','/culture/training/verifications').json()==[]
        assert get('manager','/culture/training/verifications').json()==[]
        assert get('manager',f'/culture/training/verifications/{ident}/events').status_code==403
        assert post('admin',f'/culture/training/verifications/{ident}/decision',{'decision':'Rejected','note':'Add a completion reference before verification'}).status_code==200
        assert post('admin',f'/culture/training/verifications/{ident}/decision',{'decision':'Verified','note':'No'}).status_code==422
        assert post('one','/culture/training/verifications',{'enrollment_id':enid,'evidence_note':'Completion reference 2026-TST-023 confirmed for training'}).status_code==201
        assert post('admin',f'/culture/training/verifications/{ident}/decision',{'decision':'Verified','note':'Reviewed certificate reference and completion evidence'}).status_code==200
        assert get('one','/culture/training/verifications').json()[0]['status']=='Verified'
        assert len(get('one',f'/culture/training/verifications/{ident}/events').json())==4
        assert post('one','/culture/training/verifications',{'enrollment_id':enid,'evidence_note':'Cannot request again once verified'}).status_code==409
        # Confidential case status timelines are restricted and contain NO case narrative.
        concern=post('one','/voice/cases',{'category':'Workplace concern','title':'Confidential test submission',
            'description':'Synthetic private report for role permission tests only.'})
        assert concern.status_code==201,concern.text
        cid2=concern.json()['id']
        assert get('manager',f'/culture/cases/voice/{cid2}/history').status_code==403
        assert get('two',f'/culture/cases/voice/{cid2}/history').status_code==403
        assert post('admin',f'/voice/cases/{cid2}/decision',{'status':'In Review'}).status_code==200
        vh=get('one',f'/culture/cases/voice/{cid2}/history').json()
        assert [row['new_status'] for row in vh]==['Submitted','In Review']
        assert 'Synthetic private report' not in str(vh)
        conduct=post('admin','/discipline/cases',{'employee_id':3,'category':'Policy concern',
            'summary':'Synthetic incident for restricted access testing only.', 'incident_date':'2026-10-01'})
        assert conduct.status_code==201,conduct.text
        did=conduct.json()['id']
        assert get('one',f'/culture/cases/discipline/{did}/history').status_code==403
        assert get('manager',f'/culture/cases/discipline/{did}/history').status_code==403
        assert post('admin',f'/discipline/cases/{did}/status',{'status':'Notified'}).status_code==200
        dh=get('one',f'/culture/cases/discipline/{did}/history').json()
        assert [row['new_status'] for row in dh]==['Draft','Notified']
        assert get('two',f'/culture/cases/discipline/{did}/history').status_code==403
        assert 'Synthetic incident' not in str(dh)
        # Recognition: peer-only applause, toggle reliably and count is stable.
        rec=post('one','/recognitions',{'recipient_id':4,'value':'Teamwork','message':'Great teamwork with the recent release'})
        assert rec.status_code==201,rec.text
        rid=rec.json()['id']
        assert post('one',f'/culture/recognition/{rid}/applaud').status_code==403
        assert post('two',f'/culture/recognition/{rid}/applaud').status_code==403
        assert post('three',f'/culture/recognition/{rid}/applaud').json()['applauded'] is True
        assert post('three',f'/culture/recognition/{rid}/applaud').json()['applauded'] is False
        assert post('manager',f'/culture/recognition/{rid}/applaud').json()['applauded'] is True
        reactions=get('manager','/culture/recognition/reactions').json()
        assert reactions[0]['total']==1 and reactions[0]['mine']==1
        assert get('one','/culture/recognition/reactions').json()[0]['mine']==0
        # Verify schema created. No data seeding beyond synthetic fixture.
        with main.db() as c:
            assert all(c.execute('SELECT 1 FROM sqlite_master WHERE type="table" AND name=?',(t,)).fetchone()
                       for t in ('goal_progress_history','training_verifications','training_verification_events','recognition_reactions'))
        print('PASS Culture Ops v1.9: goal history, milestone completion, training reviews, private evidence, peer applause')

"""Isolated hiring-pipeline workflow and role-access regression checks; no live HR data."""
import os,tempfile
from pathlib import Path
os.environ.update(SASS_HRM_TESTING='1',DB_ENGINE='sqlite',JWT_SECRET='hiring-pipeline-integration-test-secret-1234567890')
from fastapi.testclient import TestClient
with tempfile.TemporaryDirectory() as root:
    os.environ['DATABASE_PATH']=str(Path(root)/'hrm.db')
    import main
    with TestClient(main.app) as client:
        with main.db() as c:
            for code,name,email,role in [('A1','HR admin','admin@invalid.test','admin'),('M1','Recruiting manager','manager@invalid.test','manager'),('E1','Staff','staff@invalid.test','employee')]:
                c.execute('''INSERT INTO employees(code,name,email,role,designation,department,location,join_date,password_hash,account_active)
                    VALUES(?,?,?,?,?,?,?,?,?,1)''',(code,name,email,role,'Staff','People','Hyderabad','2026-01-01',main.hash_password('StrongPass433!')))
        auth={}
        for name,email in [('admin','admin@invalid.test'),('manager','manager@invalid.test'),('employee','staff@invalid.test')]:
            result=client.post('/api/auth/login',json={'email':email,'password':'StrongPass433!'})
            assert result.status_code==200,result.text
            auth[name]={'Authorization':'Bearer '+result.json()['token']}
        def req(role,method,path,payload=None):
            return client.request(method,'/api'+path,json=payload,headers=auth[role])
        job=req('admin','POST','/recruitment/jobs',{'title':'Platform Engineer','department':'Engineering','location':'Hyderabad','employment_type':'Full-time','openings':2})
        assert job.status_code==201,job.text
        job_id=job.json()['id']
        c=req('manager','POST','/candidates',{'name':'Candidate One','job_title':'Platform Engineer','source':'Referral'})
        assert c.status_code==201,c.text
        cid=c.json()['id']; prefix=f'/talent/hiring/candidates/{cid}'
        board=req('employee','GET','/talent/hiring/board')
        assert board.status_code==403
        board=req('manager','GET','/talent/hiring/board')
        assert board.status_code==200 and len(board.json()['stages'])==7
        assert next(x['total'] for x in board.json()['stages'] if x['stage']=='Applied')==1
        assert board.json()['permissions']['can_make_offers'] is False
        assert req('employee','GET',prefix+'/review').status_code==403
        assert req('manager','PATCH',f'/candidates/{cid}/stage',{'stage':'Offer'}).status_code==403
        assert req('manager','POST','/candidate-library',{'name':'Injected privilege candidate','job_title':'Engineer','stage':'Hired'}).status_code==403
        assert req('employee','GET',f'/talent/hiring/jobs/{job_id}/requirements').status_code==403
        assert req('manager','PUT',f'/talent/hiring/jobs/{job_id}/requirements',{'required_skills':'Python'}).status_code==403
        updated=req('admin','PUT',f'/talent/hiring/jobs/{job_id}/requirements',{'required_skills':'SQL, Python','education':'Bachelor degree','min_experience_years':3,'criteria':'Backend API design'})
        assert updated.status_code==200,updated.text
        role_data=req('manager','GET',f'/talent/hiring/jobs/{job_id}/requirements').json()
        assert role_data['requirements']['required_skills']=='SQL, Python' and role_data['requirements']['min_experience_years']==3
        assert req('admin','PUT',f'/talent/hiring/jobs/{job_id}/requirements',{'min_experience_years':100}).status_code==422
        applied=req('manager','GET',prefix+'/review').json()
        assert applied['stage']=='Applied' and len(applied['requirements'])==3
        assert req('manager','POST',prefix+'/transition',{'from_stage':'Applied','to_stage':'Screening','reason':'Qualified application'}).status_code==409
        assert req('manager','PUT',prefix+'/review',{'stage':'Applied','completed':['Fake requirement'],'note':'Verified all requirements','details':{'eligibility_summary':'Reviewed eligibility summary'}}).status_code==422
        first=req('manager','PUT',prefix+'/review',{'stage':'Applied','completed':applied['requirements'],'note':'Reviewed contact details and qualifications','details':{'eligibility_summary':'Initial experience and degree confirmed'}})
        assert first.status_code==200,first.text
        assert req('manager','POST',prefix+'/transition',{'from_stage':'Applied','to_stage':'Offer','reason':'This should not skip stages'}).status_code==409
        forward=req('manager','POST',prefix+'/transition',{'from_stage':'Applied','to_stage':'Screening','reason':'Verified initial eligibility'})
        assert forward.status_code==200,forward.text
        assert req('manager','POST',prefix+'/transition',{'from_stage':'Applied','to_stage':'Screening','reason':'Stale update should fail'}).status_code==409
        assert req('manager','PUT',prefix+'/review',{'stage':'Applied','completed':[],'note':''}).status_code==409
        for stage,target in [('Screening','Assessment'),('Assessment','Interview')]:
            review=req('manager','GET',prefix+'/review').json()
            assert review['stage']==stage
            assert req('manager','PUT',prefix+'/review',{'stage':stage,'completed':review['requirements'],'note':'Assessment outcomes reviewed and confirmed','details':{'screening_outcome':'Qualified','skill_evidence':'Verified backend skills'} if stage=='Screening' else {'assessment_type':'Coding task','assessment_score':'86','evaluator':'Manager'}}).status_code==200
            move=req('manager','POST',prefix+'/transition',{'from_stage':stage,'to_stage':target,'reason':'Competency requirements verified'})
            assert move.status_code==200,move.text
        interview=req('manager','GET',prefix+'/review').json()
        assert interview['stage']=='Interview'
        assert req('manager','PUT',prefix+'/review',{'stage':'Interview','completed':interview['requirements'],'note':'Panel feedback reviewed','details':{'interview_date':'2026-11-16','panel_feedback':'Good systems discussion','recommendation':'Recommended'}}).status_code==200
        assert req('manager','POST',prefix+'/transition',{'from_stage':'Interview','to_stage':'Offer','reason':'Panel recommendations accepted'}).status_code==403
        assert req('manager','PUT',f'/talent/hiring/jobs/{job_id}/requirements',{'required_skills':'override'}).status_code==403
        assert req('manager','PUT',prefix+'/review',{'stage':'Offer','completed':[],'note':'x'}).status_code==409
        assert req('admin','POST',prefix+'/transition',{'from_stage':'Interview','to_stage':'Offer','reason':'HR approved offer preparation'}).status_code==200
        assert req('manager','PUT',prefix+'/review',{'stage':'Offer','completed':[],'note':'x'}).status_code==403
        offer=req('admin','GET',prefix+'/review').json()
        assert req('admin','PUT',prefix+'/review',{'stage':'Offer','completed':offer['requirements'],'note':'Offer conditions checked by HR','details':{'approval_reference':'HR-APPROVAL-2026','offer_status':'Accepted'}}).status_code==200
        assert req('manager','POST',prefix+'/transition',{'from_stage':'Offer','to_stage':'Hired','reason':'No authorization to hire'}).status_code==403
        assert req('admin','POST',prefix+'/transition',{'from_stage':'Offer','to_stage':'Hired','reason':'Signed offer and joining confirmed'}).status_code==200
        assert req('admin','POST',prefix+'/transition',{'from_stage':'Hired','to_stage':'Rejected','reason':'Invalid final transition'}).status_code==409
        timeline=req('admin','GET',prefix+'/review').json()['history']
        assert len(timeline)==5 and timeline[0]['to_stage']=='Hired'
        c2=req('manager','POST','/candidates',{'name':'Candidate Two','job_title':'Platform Engineer','source':'Careers Portal'}).json()['id']
        p2=f'/talent/hiring/candidates/{c2}'
        assert req('manager','POST',p2+'/transition',{'from_stage':'Applied','to_stage':'Rejected','reason':'Does not meet the advertised experience'}).status_code==200
        assert req('manager','POST',p2+'/transition',{'from_stage':'Rejected','to_stage':'Applied','reason':'New evidence submitted'}).status_code==403
        assert req('admin','POST',p2+'/transition',{'from_stage':'Rejected','to_stage':'Applied','reason':'HR authorized reopened application'}).status_code==200
        events=req('admin','GET',p2+'/review').json()['history'];assert len(events)==2
        audit=req('admin','GET','/audit').json()
        assert any(a['action']=='hiring.stage.transition' for a in audit)
        print('PASS hiring workflow: seven windows, eligibility, checklist, audit, job requirements, manager/HR permissions, transitions and reopening')

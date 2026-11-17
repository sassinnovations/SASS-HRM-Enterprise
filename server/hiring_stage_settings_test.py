"""Isolated tests for configurable hiring stage requirements and permissions.
Uses a temporary SQLite database; NEVER connects to production MySQL.
"""
import os
import tempfile
from pathlib import Path
os.environ.update(SASS_HRM_TESTING='1', DB_ENGINE='sqlite',
                  JWT_SECRET='hiring-stage-settings-test-secret-long-enough-0123456789')
from fastapi.testclient import TestClient

with tempfile.TemporaryDirectory() as tmp:
    os.environ['DATABASE_PATH']=str(Path(tmp)/'hrm.db')
    import main
    with TestClient(main.app) as client:
        with main.db() as db:
            for code,name,mail,role in [('H1','HR admin','hr@invalid.test','admin'),
                                        ('R1','Recruit manager','recruiter@invalid.test','manager'),
                                        ('E1','Employee','employee@invalid.test','employee')]:
                db.execute('''INSERT INTO employees(code,name,email,role,designation,department,location,join_date,password_hash,account_active)
                    VALUES(?,?,?,?,?,?,?,?,?,1)''',(code,name,mail,role,'Analyst','HR','Hyderabad','2026-01-01',main.hash_password('Password433!')))
        creds={}
        for who,mail in [('admin','hr@invalid.test'),('manager','recruiter@invalid.test'),('employee','employee@invalid.test')]:
            r=client.post('/api/auth/login',json={'email':mail,'password':'Password433!'})
            assert r.status_code==200,r.text
            creds[who]={'Authorization':'Bearer '+r.json()['token']}
        def call(who,method,endpoint,data=None):
            return client.request(method,'/api'+endpoint,headers=creds[who],json=data)
        stagepath='/talent/hiring/stages/'
        for stage in ('Applied','Screening','Assessment','Interview','Offer','Hired','Rejected'):
            info=call('manager','GET',stagepath+stage+'/settings')
            assert info.status_code==200,info.text
            assert info.json()['settings']['checklist'] and info.json()['settings']['sla_days']>=1
            assert info.json()['can_edit'] is False
            assert call('employee','GET',stagepath+stage+'/settings').status_code==403
        assert call('employee','PUT',stagepath+'Applied/settings',{}).status_code==403
        applied={'checklist':['Contact and consent verified','Education and role verified'],
                 'instructions':'Verify applicant consent and application completeness before screening.',
                 'sla_days':4,'reviewer_role':'manager','note_min_chars':25}
        assert call('manager','PUT',stagepath+'Applied/settings',applied).status_code==403
        assert call('admin','PUT',stagepath+'Offer/settings',{**applied,'reviewer_role':'manager'}).status_code==422
        assert call('admin','PUT',stagepath+'Hired/settings',{**applied,'reviewer_role':'manager'}).status_code==422
        assert call('admin','PUT',stagepath+'Applied/settings',{**applied,'checklist':['Duplicate','duplicate']}).status_code==422
        assert call('admin','PUT',stagepath+'Applied/settings',{**applied,'checklist':[]}).status_code==422
        changed=call('admin','PUT',stagepath+'Applied/settings',applied)
        assert changed.status_code==200,changed.text
        assert changed.json()['settings']['note_min_chars']==25
        with main.db() as db:
            assert db.execute('SELECT COUNT(*) FROM hiring_stage_settings').fetchone()[0]==1
        # Candidate review consumes configured requirements, not old hardcoded checklist.
        cid=call('manager','POST','/candidates',{'name':'Stage Test Applicant','job_title':'Engineer','source':'Referral'}).json()['id']
        prefix=f'/talent/hiring/candidates/{cid}'
        review=call('manager','GET',prefix+'/review').json()
        assert review['requirements']==applied['checklist']
        evidence={'eligibility_summary':'Confirmed application eligibility'}
        assert call('manager','PUT',prefix+'/review',{'stage':'Applied','completed':[applied['checklist'][0]],'note':'Detailed qualification review for stage evidence','details':evidence}).status_code==200
        assert call('manager','POST',prefix+'/transition',{'from_stage':'Applied','to_stage':'Screening','reason':'All checks confirmed'}).status_code==409
        assert call('manager','PUT',prefix+'/review',{'stage':'Applied','completed':applied['checklist'],'note':'Too short','details':evidence}).status_code==200
        assert call('manager','POST',prefix+'/transition',{'from_stage':'Applied','to_stage':'Screening','reason':'All checks confirmed'}).status_code==409
        assert call('manager','PUT',prefix+'/review',{'stage':'Applied','completed':applied['checklist'],'note':'Both checks and consent verified against provided evidence','details':evidence}).status_code==200
        assert call('manager','POST',prefix+'/transition',{'from_stage':'Applied','to_stage':'Screening','reason':'All checks confirmed'}).status_code==200
        screening=call('admin','GET',stagepath+'Screening/settings').json()['settings']
        screening['reviewer_role']='admin'
        assert call('admin','PUT',stagepath+'Screening/settings',screening).status_code==200
        assert call('manager','PUT',prefix+'/review',{'stage':'Screening','completed':[],'note':'something'}).status_code==403
        assert call('manager','POST',prefix+'/transition',{'from_stage':'Screening','to_stage':'Rejected','reason':'Not qualified after screening'}).status_code==403
        assert call('admin','PUT',prefix+'/review',{'stage':'Screening','completed':[],'note':'Some HR notes'}).status_code==200
        assert call('admin','POST',prefix+'/transition',{'from_stage':'Screening','to_stage':'Rejected','reason':'Qualifications do not meet minimum role criteria'}).status_code==200
        assert call('manager','POST',prefix+'/transition',{'from_stage':'Rejected','to_stage':'Applied','reason':'Reopen applicant'}).status_code==403
        assert call('admin','POST',prefix+'/transition',{'from_stage':'Rejected','to_stage':'Applied','reason':'New supporting evidence submitted'}).status_code==200
        assert call('admin','GET','/talent/hiring/board').json()['stages'][0]['checklist']==applied['checklist']
        aud=call('admin','GET','/audit').json()
        assert any(x['action']=='hiring.stage.settings' for x in aud)
        print('PASS: seven hiring stage settings, role permissions, validation, dynamic checklist and note gates, HR-only Offer/Hired and audit')

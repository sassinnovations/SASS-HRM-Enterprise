"""Isolated regression: official work details can be proposed by staff/sub-admin and approved by HR."""
import os
import tempfile
from pathlib import Path

os.environ['SASS_HRM_TESTING']='1'
os.environ['DB_ENGINE']='sqlite'
os.environ['JWT_SECRET']='ISOLATED-OFFICIAL-ALL-ROLES-TEST-SECRET-MORE-THAN-40-CHARACTERS'
from fastapi.testclient import TestClient

with tempfile.TemporaryDirectory() as tmp:
    os.environ['DATABASE_PATH']=str(Path(tmp)/'test.db')
    import main
    from accounts_v25 import save_tier
    with TestClient(main.app) as client:
        secret='StrongPassword456!'
        for code,name,email,role,tier in [
            ('SASSADM','HR Admin','admin@example.org','admin','admin'),
            ('SASSMGR','HR Sub Admin','sub@example.org','manager','hr_subadmin'),
            ('SASSSTA','Employee One','staff@example.org','employee','employee'),
            ('SASSOTH','Employee Two','other@example.org','employee','employee')]:
            with main.db() as conn:
                r=conn.execute('''INSERT INTO employees(code,name,email,work_email,role,designation,department,location,work_mode,join_date,password_hash,account_active)
                  VALUES(?,?,?,?,?,?,?,?,?,?,?,1)''',(code,name,email,email,role,'Associate','Operations','Hyderabad','Hybrid','2026-01-02',main.hash_password(secret)))
                save_tier(conn,r.lastrowid,tier)
        def auth(email):
            r=client.post('/api/auth/login',json={'email':email,'password':secret})
            assert r.status_code==200,r.text
            return {'Authorization':'Bearer '+r.json()['token']}
        admin,sub,staff,other=[auth(email) for email in ('admin@example.org','sub@example.org','staff@example.org','other@example.org')]
        for head,role,tier in [(admin,'admin','admin'),(sub,'manager','hr_subadmin'),(staff,'employee','employee')]:
            r=client.get('/api/profile/me',headers=head)
            assert r.status_code==200,r.text
            assert r.json()['role']==role and r.json()['access_tier']==tier
        template=client.get('/api/profile/me',headers=staff).json()
        values={k:template[k] for k in ('code','name','work_email','designation','department','location','work_mode','join_date')}
        values['designation']='Software Engineer'
        values['change_reason']='Promotion record correction'
        endpoint='/api/profile/me/official-change-requests'
        assert client.post(endpoint,json=values).status_code==401
        assert client.post(endpoint,headers=staff,json={**values,'role':'admin'}).status_code==422
        assert client.post(endpoint,headers=staff,json={**values,'code':'!!!'}).status_code==422
        assert client.post(endpoint,headers=staff,json={**values,'join_date':'2026-02-30'}).status_code==422
        request=client.post(endpoint,headers=staff,json=values)
        assert request.status_code==201,request.text
        reqid=request.json()['id']
        assert client.get('/api/profile/me',headers=staff).json()['designation']=='Associate', 'Must not change record before approval'
        assert client.post(endpoint,headers=staff,json=values).status_code==409, 'Only one pending request'
        assert client.get('/api/profile/admin/official-change-requests',headers=staff).status_code==403
        assert client.post(f'/api/profile/admin/official-change-requests/{reqid}/decision',headers=staff,json={'decision':'Approved'}).status_code==403
        assert client.get(endpoint,headers=other).json()==[], 'No cross-employee requests'
        r=client.post(f'/api/profile/admin/official-change-requests/{reqid}/decision',headers=admin,json={'decision':'Approved'})
        assert r.status_code==200,r.text
        assert client.get('/api/profile/me',headers=staff).json()['designation']=='Software Engineer'
        assert client.post(f'/api/profile/admin/official-change-requests/{reqid}/decision',headers=admin,json={'decision':'Approved'}).status_code==409
        assert client.get(endpoint,headers=staff).json()[0]['status']=='Approved'
        # Sub-admin can submit for their own profile but cannot self-approve or view all requests.
        sub_me=client.get('/api/profile/me',headers=sub).json()
        sub_val={k:sub_me[k] for k in ('code','name','work_email','designation','department','location','work_mode','join_date')}
        sub_val.update({'department':'Human Resources','change_reason':'Department record correction'})
        rq=client.post(endpoint,headers=sub,json=sub_val)
        assert rq.status_code==201,rq.text
        sub_id=rq.json()['id']
        assert client.get('/api/profile/admin/official-change-requests',headers=sub).status_code==403
        assert client.post(f'/api/profile/admin/official-change-requests/{sub_id}/decision',headers=sub,json={'decision':'Approved'}).status_code==403
        assert client.post(f'/api/profile/admin/official-change-requests/{sub_id}/decision',headers=admin,json={'decision':'Rejected','review_note':'Needs documents'}).status_code==200
        assert client.get('/api/profile/me',headers=sub).json()['department']=='Operations', 'Rejected request cannot update employee'
        # Old baseline cannot overwrite another HR admin edit.
        newval={**values,'designation':'Senior Software Engineer','change_reason':'Correction for seniority'}
        stale=client.post(endpoint,headers=staff,json=newval)
        assert stale.status_code==201,stale.text
        stale_id=stale.json()['id']
        admin_patch=client.patch('/api/admin/accounts/3/profile',headers=admin,json={
            'name':'Employee One','email':'staff@example.org','work_email':'staff@example.org','designation':'Tech Lead',
            'department':'Operations','location':'Hyderabad','work_mode':'Hybrid','change_reason':'Management update'})
        assert admin_patch.status_code==200,admin_patch.text
        conflict=client.post(f'/api/profile/admin/official-change-requests/{stale_id}/decision',headers=admin,json={'decision':'Approved'})
        assert conflict.status_code==409,conflict.text
        assert client.get('/api/profile/me',headers=staff).json()['designation']=='Tech Lead'
        assert client.post(f'/api/profile/admin/official-change-requests/{stale_id}/decision',headers=admin,json={'decision':'Rejected','review_note':'Record changed'}).status_code==200
        # HR admin profile still edits directly, existing path (no request created).
        admin_me=client.get('/api/profile/me',headers=admin).json()
        admin_payload={k:admin_me[k] for k in ('code','name','work_email','designation','department','location','work_mode','join_date')}
        admin_payload['email']=admin_me['email']
        admin_payload['location']='Bengaluru'
        admin_payload['change_reason']='Update work location'
        result=client.patch('/api/admin/accounts/1/profile',headers=admin,json=admin_payload)
        assert result.status_code==200,result.text
        assert client.get('/api/profile/me',headers=admin).json()['location']=='Bengaluru'
        assert client.post(endpoint,headers=admin,json=admin_payload).status_code in (403,422)
        with main.db() as conn:
            actions={r['action'] for r in conn.execute('SELECT action FROM audit_events')}
            assert 'profile.official_change.requested' in actions
            assert 'profile.official_change.approved' in actions
            assert 'profile.official_change.rejected' in actions
            assert 'identity.profile_updated' in actions
        print('PASS: employee/sub-admin request, HR approval/reject, live profile persistence, audit, isolation, stale safeguards')

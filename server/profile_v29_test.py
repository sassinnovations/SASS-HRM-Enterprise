"""Isolated profile permissions, persistence, privacy and HR change control."""
import os
import tempfile
from pathlib import Path
os.environ['SASS_HRM_TESTING']='1'
os.environ['DB_ENGINE']='sqlite'
os.environ['JWT_SECRET']='PROFILE-ISOLATED-TEST-ONLY-SECRET-LONGER-THAN-FORTY-CHARS'
from fastapi.testclient import TestClient
with tempfile.TemporaryDirectory() as temporary:
    os.environ['DATABASE_PATH']=str(Path(temporary)/'profile-tests.db')
    import main
    from main import hash_password,db
    with TestClient(main.app) as client:
        with db() as conn:
            entries=[('ADM-101','Admin User','admin@example.org','admin'),('EMP-201','Employee One','one@example.org','employee'),('EMP-202','Employee Two','two@example.org','employee')]
            for code,name,email,role in entries:
                conn.execute('''INSERT INTO employees(code,name,email,role,designation,department,location,work_mode,join_date,manager_id,password_hash,account_active)
                VALUES(?,?,?,?,?,?,?,?,?,?,?,1)''',(code,name,email,role,'Engineer','Engineering','Hyderabad','Hybrid','2026-09-01',None,hash_password('StrongAdminPassword12345!')))
        def header(email):
            res=client.post('/api/auth/login',json={'email':email,'password':'StrongAdminPassword12345!'})
            assert res.status_code==200,res.text
            return {'Authorization':'Bearer '+res.json()['token']}
        admin=header('admin@example.org');first=header('one@example.org');second=header('two@example.org')
        assert client.get('/api/profile/me').status_code==401
        assert client.get('/api/profile/admin/overview',headers=first).status_code==403
        assert client.get('/api/profile/admin/requests',headers=first).status_code==403
        assert client.get('/api/profile/me',headers=first).json()['name']=='Employee One'
        before=client.get('/api/profile/directory',headers=second).json()
        assert len(before)==3
        payload={'preferred_name':'E. One','headline':'Software Engineer','biography':'Builds HR systems','work_phone':'+91 99900 11122','timezone':'Asia/Kolkata','language':'te','directory_visible':False,'avatar_color':'#5F5CEB'}
        changed=client.put('/api/profile/me',headers=first,json=payload)
        assert changed.status_code==200,changed.text
        assert changed.json()['preferred_name']=='E. One'
        assert client.get('/api/profile/me',headers=first).json()['biography']=='Builds HR systems'
        assert len(client.get('/api/profile/directory',headers=second).json())==2
        assert 'Employee One' not in str(client.get('/api/profile/directory',headers=second).json())
        bad=client.put('/api/profile/me',headers=first,json={**payload,'avatar_color':'javascript:alert(1)'})
        assert bad.status_code==422
        bad=client.put('/api/profile/me',headers=first,json={**payload,'timezone':'Unknown/Planet'})
        assert bad.status_code==422
        assert client.get('/api/profile/admin/overview',headers=admin).status_code==200
        for v in client.get('/api/profile/admin/overview',headers=admin).json():
            assert 'biography' not in v and 'password_hash' not in v and 'mailing_address' not in v
        assert client.get('/api/profile/me/requests',headers=second).json()==[]
        requested=client.post('/api/profile/me/requests',headers=first,json={'requested_value':'Employee Corrected','reason':'Official employment name is inaccurate'})
        assert requested.status_code==201,requested.text
        id=requested.json()['id']
        assert client.post('/api/profile/me/requests',headers=first,json={'requested_value':'Second Request','reason':'The same field needs correction'}).status_code==409
        assert client.get('/api/profile/me/requests',headers=second).json()==[]
        assert client.post(f'/api/profile/admin/requests/{id}/decision',headers=second,json={'decision':'Approved'}).status_code==403
        assert client.post(f'/api/profile/admin/requests/{id}/decision',headers=admin,json={'decision':'Approved'}).status_code==200
        assert client.get('/api/profile/me',headers=first).json()['name']=='Employee Corrected'
        assert client.post(f'/api/profile/admin/requests/{id}/decision',headers=admin,json={'decision':'Approved'}).status_code==409
        assert client.post('/api/profile/me/requests',headers=admin,json={'requested_value':'Another Admin Name','reason':'Correction requested by admin'}).status_code==201
        admin_req=client.get('/api/profile/me/requests',headers=admin).json()[0]['id']
        assert client.post(f'/api/profile/admin/requests/{admin_req}/decision',headers=admin,json={'decision':'Approved'}).status_code==403
        other=client.post('/api/profile/me/requests',headers=second,json={'requested_value':'Corrected Two','reason':'Correct name is different'})
        assert other.status_code==201
        second_id=other.json()['id']
        assert client.post(f'/api/profile/admin/requests/{second_id}/decision',headers=admin,json={'decision':'Rejected','review_note':'no'}).status_code==422
        assert client.post(f'/api/profile/admin/requests/{second_id}/decision',headers=admin,json={'decision':'Rejected','review_note':'Please contact HR with supporting details.'}).status_code==200
        with db() as conn:
            audit_actions=[r[0] for r in conn.execute('SELECT action FROM audit_events').fetchall()]
        assert 'profile.self_updated' in audit_actions and 'profile.correction.requested' in audit_actions
        assert 'profile.correction.approved' in audit_actions and 'profile.correction.rejected' in audit_actions
        print('PASS: professional profile persistence, directory visibility, validation, HR-only review, self-review denied, audits')

"""v2.0 isolated permission and mutation tests. Synthetic account records; never connect to real MySQL."""
import os, tempfile
from pathlib import Path
os.environ.update(SASS_HRM_TESTING='1', DB_ENGINE='sqlite', JWT_SECRET='employee-services-test-secret-string-over-40-characters-abc123')
from fastapi.testclient import TestClient

with tempfile.TemporaryDirectory() as path:
    os.environ['DATABASE_PATH'] = str(Path(path) / 'isolated-services.db')
    import main
    with TestClient(main.app) as c:
        with main.db() as db:
            for code,name,mail,role in [
                ('H1','Test HR','hr@example.invalid','admin'),
                ('E1','Synthetic One','one@example.invalid','employee'),
                ('E2','Synthetic Two','two@example.invalid','employee'),
                ('M1','Synthetic Manager','manager@example.invalid','manager'),
            ]:
                db.execute('''INSERT INTO employees(code,name,email,role,designation,department,location,join_date,password_hash,account_active)
                    VALUES(?,?,?,?,?,?,?,?,?,1)''', (code,name,mail,role,'Analyst','Engineering','Chennai','2026-01-01',main.hash_password('SyntheticTestPass123!')))
        users={}
        for key in ('hr','one','two','manager'):
            res=c.post('/api/auth/login',json={'email':f'{key}@example.invalid','password':'SyntheticTestPass123!'})
            assert res.status_code==200,(key,res.text)
            users[key]={'Authorization':'Bearer '+res.json()['token']}
        def get(w,path):return c.get('/api'+path,headers=users[w])
        def post(w,path,data):return c.post('/api'+path,headers=users[w],json=data)
        def put(w,path,data):return c.put('/api'+path,headers=users[w],json=data)
        asset=post('hr','/assets',{'employee_id':2,'asset_name':'Synthetic laptop','serial_number':'TEST-ASSET-100'})
        assert asset.status_code==201,asset.text
        aid=asset.json()['id']
        assert post('one',f'/assets/{aid}/lifecycle',{'action':'Return'}).status_code==403
        assert get('two',f'/assets/{aid}/lifecycle').status_code==403
        assert post('hr',f'/assets/{aid}/lifecycle',{'action':'Restore to service'}).status_code==409
        assert post('hr',f'/assets/{aid}/lifecycle',{'action':'Transfer','new_employee_id':2}).status_code==422
        assert post('hr',f'/assets/{aid}/lifecycle',{'action':'Send for repair','note':'Routine repair'}).json()['status']=='Maintenance'
        assert post('hr',f'/assets/{aid}/lifecycle',{'action':'Return'}).json()['status']=='Returned'
        assert post('hr',f'/assets/{aid}/lifecycle',{'action':'Transfer','new_employee_id':3}).status_code==409
        assert post('hr',f'/assets/{aid}/lifecycle',{'action':'Reassign','new_employee_id':3}).json()['employee_id']==3
        assert get('one','/assets').json()==[]
        assert len(get('two','/assets').json())==1
        assert get('one',f'/assets/{aid}/lifecycle').status_code==403
        assert len(get('two',f'/assets/{aid}/lifecycle').json())==3
        assert 'note' not in str(get('two',f'/assets/{aid}/lifecycle').json())
        assert len(get('hr',f'/assets/{aid}/lifecycle').json())==3
        doc=post('hr','/documents',{'employee_id':2,'title':'Synthetic compliance receipt','document_type':'Compliance'})
        assert doc.status_code==201,doc.text
        did=doc.json()['id']
        assert post('one',f'/documents/{did}/review',{'decision':'Verified'}).status_code==403
        assert get('two',f'/documents/{did}/reviews').status_code==403
        assert post('hr',f'/documents/{did}/review',{'decision':'Rejected','note':'x'}).status_code==422
        assert post('hr',f'/documents/{did}/review',{'decision':'Verified','expires_on':'2020-01-01'}).status_code==422
        assert post('hr',f'/documents/{did}/review',{'decision':'Rejected','note':'Missing document reference'}).status_code==200
        assert post('hr',f'/documents/{did}/review',{'decision':'Verified','expires_on':'2028-08-01'}).status_code==200
        assert get('one','/documents').json()[0]['status']=='Verified'
        assert len(get('one',f'/documents/{did}/reviews').json())==2
        assert 'Missing document reference' not in str(get('one',f'/documents/{did}/reviews').json())
        assert get('hr',f'/documents/{did}/reviews').json()[1]['note']=='Missing document reference'
        assert get('one','/me/preferences').json()['density']=='Comfortable'
        assert put('one','/me/preferences',{'density':'Compact','date_format':'YYYY-MM-DD','reduce_motion':True}).status_code==200
        assert get('one','/me/preferences').json()['reduce_motion'] is True
        assert get('two','/me/preferences').json()['density']=='Comfortable'
        assert put('one','/me/preferences',{'density':'Unsafe'}).status_code==422
        assert get('manager','/admin/employee-services/summary').status_code==403
        assert get('hr','/admin/employee-services/summary').json()['documents_pending']==0
        assert get('one','/ai/capabilities').json()['write_actions'] is False
        with main.db() as db:
            assert db.execute("SELECT COUNT(*) FROM audit_events WHERE action='asset.lifecycle'").fetchone()[0]==3
            assert db.execute("SELECT COUNT(*) FROM audit_events WHERE action='document.reviewed'").fetchone()[0]==2
        print('PASS v2.0 Employee Services: asset transfers, maintenance, returns, document reviews, privacy, preferences, audit')

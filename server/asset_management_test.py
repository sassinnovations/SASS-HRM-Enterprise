"""Isolated API regression for enriched asset register; never writes live MySQL."""
import os
import tempfile
from pathlib import Path
os.environ.update(SASS_HRM_TESTING='1', DB_ENGINE='sqlite', JWT_SECRET='asset-register-test-secret-should-be-longer-than-40-chars')
from fastapi.testclient import TestClient
with tempfile.TemporaryDirectory() as path:
    os.environ['DATABASE_PATH']=str(Path(path)/'isolated-assets.db')
    import main
    with TestClient(main.app) as client:
        with main.db() as c:
            for code, name, email, role in [('ADMIN','Test HR','admin@example.invalid','admin'),
                                            ('STAFF1','Employee One','one@example.invalid','employee'),
                                            ('STAFF2','Employee Two','two@example.invalid','employee'),
                                            ('MANAGER','Test Manager','manager@example.invalid','manager')]:
                c.execute('''INSERT INTO employees(code,name,email,role,designation,department,location,join_date,password_hash,account_active)
                             VALUES(?,?,?,?,?,?,?,?,?,1)''', (code,name,email,role,'Tester','IT','Hyderabad','2026-01-01',main.hash_password('SyntheticPass123!')))
        headers={}
        for role in ['admin','one','two','manager']:
            result=client.post('/api/auth/login',json={'email':f'{role}@example.invalid','password':'SyntheticPass123!'})
            assert result.status_code==200,(role,result.text)
            headers[role]={'Authorization':'Bearer '+result.json()['token']}
        def call(role,method,uri,data=None):
            return client.request(method,'/api'+uri,json=data,headers=headers[role])
        new={'employee_id':2,'asset_name':'Synthetic laptop', 'serial_number':'ASSET-100',
             'category':'Laptop','description':'Synthetic laptop for testing asset inventory management',
             'condition_label':'Good','storage_location':'Hyderabad IT store','manufacturer':'Test Manufacturer',
             'model':'Model A','asset_tag':'TESTTAG-100','purchase_date':'2026-01-02',
             'purchase_amount':'45000.00','warranty_expiry':'2028-01-02','supplier_name':'Test vendor',
             'invoice_number':'INV-TEST-1','accessories':'Charger and sleeve','internal_notes':'Secret IT note'}
        assert call('one','POST','/assets/register',new).status_code==403
        assert call('manager','POST','/assets/register',new).status_code==403
        assert call('admin','POST','/assets/register',{**new,'description':'x'}).status_code==422
        assert call('admin','POST','/assets/register',{**new,'warranty_expiry':'2025-01-01'}).status_code==422
        reg=call('admin','POST','/assets/register',new)
        assert reg.status_code==201,reg.text
        aid=reg.json()['id']
        assert call('admin','POST','/assets/register',new).status_code==409
        assert len(call('admin','GET','/assets/registry').json())==1
        own=call('one','GET','/assets/registry').json()
        assert len(own)==1 and own[0]['description']==new['description']
        assert 'purchase_amount' not in own[0] and 'internal_notes' not in own[0]
        assert 'invoice_number' not in own[0] and 'supplier_name' not in own[0]
        assert call('two','GET','/assets/registry').json()==[]
        assert call('manager','GET','/assets/registry').json()==[]
        assert call('two','GET',f'/assets/{aid}/inspections').status_code==403
        assert call('one','PATCH',f'/assets/{aid}/profile',{**new,'reason':'Change asset details for test'}).status_code==403
        assert call('admin','PATCH',f'/assets/{aid}/profile',{**new,'reason':'x'}).status_code==422
        updated={**new,'model':'Model B','condition_label':'Fair','reason':'Correct the recorded model and condition'}
        changed=call('admin','PATCH',f'/assets/{aid}/profile',updated)
        assert changed.status_code==200,changed.text
        assert call('admin','GET','/assets/registry').json()[0]['model']=='Model B'
        test_inspection={'inspected_on':'2026-11-16','condition_label':'Fair',
                         'working_ok':True,'accessories_ok':False,'security_ok':True,'note':'Missing supplied accessory'}
        assert call('one','POST',f'/assets/{aid}/inspections',test_inspection).status_code==403
        assert call('admin','POST',f'/assets/{aid}/inspections',test_inspection).status_code==201
        checks=call('one','GET',f'/assets/{aid}/inspections').json()
        assert len(checks)==1 and 'note' not in checks[0]
        assert call('admin','GET',f'/assets/{aid}/inspections').json()[0]['note']=='Missing supplied accessory'
        assert call('two','POST',f'/assets/{aid}/maintenance',{'maintenance_kind':'Keyboard repair'}).status_code==403
        req=call('one','POST',f'/assets/{aid}/maintenance',{'maintenance_kind':'Keyboard repair','severity':'High'})
        assert req.status_code==201,req.text
        case=req.json()['id']
        assert call('one','PATCH',f'/assets/maintenance/{case}',{'request_status':'Resolved'}).status_code==403
        assert call('admin','PATCH',f'/assets/maintenance/{case}',{'request_status':'In Progress'}).status_code==200
        assert call('admin','PATCH',f'/assets/maintenance/{case}',{'request_status':'Resolved'}).status_code==200
        assert call('admin','PATCH',f'/assets/maintenance/{case}',{'request_status':'Open'}).status_code==409
        assert call('admin','GET',f'/assets/{aid}/maintenance').json()[0]['request_status']=='Resolved'
        assert call('admin','POST',f'/assets/{aid}/lifecycle',{'action':'Return'}).status_code==200
        assert call('one','POST',f'/assets/{aid}/maintenance',{'maintenance_kind':'Test repair'}).status_code==409
        assert call('admin','GET','/assets/registry').json()[0]['status']=='Returned'
        with main.db() as c:
            actions={r[0]:r[1] for r in c.execute('SELECT action,COUNT(*) FROM audit_events GROUP BY action')}
            assert actions['asset.registered']==1 and actions['asset.profile.updated']==1
            assert actions['asset.inspected']==1 and actions['asset.maintenance.requested']==1
            assert actions['asset.maintenance.updated']==2
            assert c.execute('SELECT COUNT(*) FROM employees').fetchone()[0]==4
        print('PASS asset management: requirements, creation, edit, authorization, privacy, inspection, maintenance, lifecycle, audit')

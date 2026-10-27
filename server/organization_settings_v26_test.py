"""Regression tests: organization settings, offices, validation, roles and audit."""
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

os.environ['SASS_HRM_TESTING']='1'
os.environ['DB_ENGINE']='sqlite'
os.environ['JWT_SECRET']='v26-isolated-unit-token-do-not-use-in-real-deployments-12345'

from fastapi.testclient import TestClient
with tempfile.TemporaryDirectory() as folder:
    os.environ['DATABASE_PATH']=str(Path(folder)/'organization.db')
    import main, create_admin
    with TestClient(main.app) as c:
        with patch.object(sys,'argv',['create_admin.py','--email','admin@example.org','--name','HR Administrator','--code','HR002','--location','Hyderabad']),patch.object(create_admin.getpass,'getpass',side_effect=['SampleAdminPassword123!!']*2):
            create_admin.main()
        auth=c.post('/api/auth/login',json={'email':'admin@example.org','password':'SampleAdminPassword123!!'})
        assert auth.status_code==200, auth.text
        hdr={'Authorization':'Bearer '+auth.json()['token']}
        prefs_url='/api/admin/organization/settings'
        office_url='/api/admin/organization/offices'
        assert c.get(prefs_url).status_code==401
        assert c.get(office_url).status_code==401
        defaults=c.get(prefs_url,headers=hdr)
        assert defaults.status_code==200 and defaults.json()['currency']=='INR'
        p={'currency':'USD','date_format':'YYYY-MM-DD','week_start':'Sunday','fiscal_year_start_month':1,'hours_per_day':7}
        response=c.put(prefs_url,headers=hdr,json=p)
        assert response.status_code==200,response.text
        assert c.get(prefs_url,headers=hdr).json()['hours_per_day']==7
        assert c.put(prefs_url,headers=hdr,json={**p,'hours_per_day':18}).status_code==422
        assert c.put(prefs_url,headers=hdr,json={**p,'currency':'BTC'}).status_code==422
        office={'code':'HYD-01','name':'SASS Hyderabad','city':'Hyderabad','country':'India','address':'HITEC City','timezone':'Asia/Kolkata','is_active':True}
        assert c.post(office_url,headers=hdr,json={**office,'timezone':'Invalid/Zone'}).status_code==422
        created=c.post(office_url,headers=hdr,json=office)
        assert created.status_code==201,created.text
        duplicate=c.post(office_url,headers=hdr,json={**office,'code':'HYD-02'})
        assert duplicate.status_code==409,duplicate.text
        offices=c.get(office_url,headers=hdr).json()
        assert len(offices)==1 and offices[0]['name']==office['name']
        office_id=offices[0]['id']
        update=c.put(f'{office_url}/{office_id}',headers=hdr,json={**office,'address':'Kondapur'})
        assert update.status_code==200,update.text
        assert c.put(f'{office_url}/9999',headers=hdr,json=office).status_code==404
        with main.db() as db:
            db.execute('''INSERT INTO employees(code,name,email,role,designation,department,location,work_mode,join_date,manager_id,password_hash,account_active)
                VALUES(?,?,?,?,?,?,?,?,?,?,?,1)''',('EMP001','Test Employee','person@example.org','employee','Engineer','Engineering','SASS Hyderabad','Hybrid','2026-01-15',None,main.hash_password('EmployeePasswordStrong123!')))
        assert c.put(f'{office_url}/{office_id}',headers=hdr,json={**office,'name':'Renamed'}).status_code==409
        assert c.put(f'{office_url}/{office_id}',headers=hdr,json={**office,'is_active':False}).status_code==409
        employee_login=c.post('/api/auth/login',json={'email':'person@example.org','password':'EmployeePasswordStrong123!'})
        assert employee_login.status_code==200,employee_login.text
        restricted={'Authorization':'Bearer '+employee_login.json()['token']}
        for endpoint in (prefs_url,office_url):
            assert c.get(endpoint,headers=restricted).status_code==403
        assert c.get('/api/organization/identity',headers=restricted).json()['name']=='SASS Innovations'
        assert c.put(prefs_url,headers=restricted,json=p).status_code==403
        assert c.post(office_url,headers=restricted,json=office).status_code==403
        assert c.put(f'{office_url}/{office_id}',headers=restricted,json=office).status_code==403
        with main.db() as db:
            actions=[r[0] for r in db.execute("SELECT action FROM audit_events WHERE action LIKE 'organization.%'").fetchall()]
        assert 'organization.preferences.updated' in actions
        assert 'organization.office.created' in actions and 'organization.office.updated' in actions
        print('PASS: persisted preferences, office CRUD, validation, no duplicate codes/names, employee protection, role restrictions, auditing')

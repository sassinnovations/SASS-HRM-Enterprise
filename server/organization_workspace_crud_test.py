"""Organization workspace CRUD, read-only employees, admin settings and audit (SQLite isolated)."""
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

os.environ.update(SASS_HRM_TESTING='1',DB_ENGINE='sqlite',JWT_SECRET='isolated-organization-workspace-validation-secret-of-at-least-50-characters')

from fastapi.testclient import TestClient
with tempfile.TemporaryDirectory() as folder:
    os.environ['DATABASE_PATH']=str(Path(folder)/'org.db')
    import main,create_admin
    with TestClient(main.app) as client:
        with patch.object(sys,'argv',['create_admin.py','--email','admin@example.org','--name','Org Administrator','--code','ORG001','--location','Hyderabad']),patch.object(create_admin.getpass,'getpass',side_effect=['SecureOrgTestPass5678!']*2):
            create_admin.main()
        response=client.post('/api/auth/login',json={'email':'admin@example.org','password':'SecureOrgTestPass5678!'})
        assert response.status_code==200,response.text
        admin={'Authorization':'Bearer '+response.json()['token']}
        def call(method,url,body=None,header=admin):
            return client.request(method,'/api'+url,headers=header,json=body)
        # Department CRUD and unique normalization.
        dep={'name':'Engineering','location':'Hyderabad','head_id':None}
        r=call('POST','/organization/departments',dep)
        assert r.status_code==201,r.text
        did=r.json()['id']
        assert call('POST','/organization/departments',{**dep,'name':'  engineering  '}).status_code==409
        assert call('POST','/organization/departments',{**dep,'name':'   '}).status_code==422
        assert call('PUT',f'/organization/departments/{did}',{**dep,'name':'Quality','location':'Mumbai'}).status_code==200
        assert call('GET','/organization/departments').json()[0]['name']=='Quality'
        assert call('DELETE',f'/organization/departments/{did}',{'confirm':'DELETE','reason':'     '}).status_code==422
        assert call('DELETE',f'/organization/departments/{did}',{'confirm':'INVALID','reason':'Org restructuring'}).status_code==422
        assert call('DELETE','/organization/departments/9876',{'confirm':'DELETE','reason':'Org restructuring'}).status_code==404
        # Department with linked employees cannot be renamed or deleted.
        with main.db() as c:
            c.execute('''INSERT INTO employees(code,name,email,role,designation,department,location,work_mode,join_date,manager_id,password_hash,account_active)
             VALUES(?,?,?,?,?,?,?,?,?,?,?,1)''',('STAFF01','Staff Member','staff@example.org','employee','Developer','Quality','Mumbai','Hybrid','2026-11-19',None,main.hash_password('SecureEmployeePassword9786!')))
        staff_login=call('POST','/auth/login',{'email':'staff@example.org','password':'SecureEmployeePassword9786!'})
        assert staff_login.status_code==200,staff_login.text
        employee={'Authorization':'Bearer '+staff_login.json()['token']}
        assert call('PUT',f'/organization/departments/{did}',{**dep,'name':'Engineering'},admin).status_code==409
        assert call('DELETE',f'/organization/departments/{did}',{'confirm':'DELETE','reason':'Org restructuring'}).status_code==409
        assert call('PUT',f'/organization/departments/{did}',{**dep,'name':'Quality','location':'Bengaluru'},admin).status_code==200
        assert call('GET','/organization/departments',None,employee).status_code==200
        assert call('POST','/organization/departments',dep,employee).status_code==403
        assert call('PUT',f'/organization/departments/{did}',dep,employee).status_code==403
        assert call('DELETE',f'/organization/departments/{did}',{'confirm':'DELETE','reason':'Unauthorized delete'},employee).status_code==403
        # Unused departments can be permanently deleted without impacting staff.
        unused=call('POST','/organization/departments',{'name':'Unused unit','location':'Pune'})
        assert unused.status_code==201,unused.text
        uid=unused.json()['id']
        assert call('DELETE',f'/organization/departments/{uid}',{'confirm':'DELETE','reason':'Never activated'}).status_code==200
        assert not any(d['id']==uid for d in call('GET','/organization/departments').json())
        # Holiday CRUD, conflict and permissions.
        holiday={'name':'Company foundation day','day':'2027-04-02','location':'All'}
        created=call('POST','/organization/holidays',holiday)
        assert created.status_code==201,created.text
        hid=created.json()['id']
        assert call('POST','/organization/holidays',{**holiday,'name':'Other holiday'}).status_code==409
        assert call('PUT',f'/organization/holidays/{hid}',{**holiday,'name':'Company anniversary','day':'2027-04-03'}).status_code==200
        assert call('PUT',f'/organization/holidays/{hid}',{**holiday,'name':'   '}).status_code==422
        assert call('PUT',f'/organization/holidays/{hid}',holiday,employee).status_code==403
        assert call('DELETE',f'/organization/holidays/{hid}',{'confirm':'DELETE','reason':'Calendar corrected'},employee).status_code==403
        assert call('DELETE',f'/organization/holidays/{hid}',{'confirm':'DELETE','reason':'Calendar corrected'}).status_code==200
        assert not call('GET','/organization/holidays').json()
        # Announcement CRUD, validation and permissions.
        a={'title':'Office hours update','body':'Our office opens at nine.'}
        published=call('POST','/organization/announcements',a)
        assert published.status_code==201,published.text
        aid=published.json()['id']
        assert call('PUT',f'/organization/announcements/{aid}',{'title':'Office hours','body':'  '}).status_code==422
        assert call('PUT',f'/organization/announcements/{aid}',{**a,'title':'New opening hours'}).status_code==200
        assert call('GET','/organization/announcements',None,employee).json()[0]['title']=='New opening hours'
        assert call('POST','/organization/announcements',a,employee).status_code==403
        assert call('PUT',f'/organization/announcements/{aid}',a,employee).status_code==403
        assert call('DELETE',f'/organization/announcements/{aid}',{'confirm':'DELETE','reason':'Incorrect notice'},employee).status_code==403
        assert call('DELETE',f'/organization/announcements/{aid}',{'confirm':'DELETE','reason':'Incorrect notice'}).status_code==200
        assert call('GET','/organization/announcements').json()==[]
        # Shared settings are already MySQL backed and admin-scoped.
        assert call('PUT','/admin/organization/settings',{'currency':'INR','date_format':'YYYY-MM-DD','week_start':'Monday','fiscal_year_start_month':4,'hours_per_day':8}).status_code==200
        assert call('GET','/admin/organization/settings',None,employee).status_code==403
        with main.db() as c:
            acts=[r['action'] for r in c.execute("SELECT action FROM audit_events WHERE action LIKE 'department.%' OR action LIKE 'holiday.%' OR action LIKE 'announcement.%'").fetchall()]
        assert {'department.created','department.updated','department.deleted','holiday.created','holiday.updated','holiday.deleted','announcement.published','announcement.updated','announcement.deleted'}.issubset(set(acts)), acts
        print('PASS: organization department, holiday and announcement CRUD, delete confirmation, RBAC, audit, preference persistence')

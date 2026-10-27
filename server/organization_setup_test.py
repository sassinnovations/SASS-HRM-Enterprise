"""Live FastAPI integration tests for v1.6 organization onboarding (isolated SQLite)."""
import os,sys,tempfile
from pathlib import Path
from unittest.mock import patch

os.environ['SASS_HRM_TESTING']='1'
os.environ['DB_ENGINE']='sqlite'
os.environ['JWT_SECRET']='v1.6-isolated-integration-secret-of-at-least-fifty-characters!!'

from fastapi.testclient import TestClient
with tempfile.TemporaryDirectory() as scratch:
 os.environ['DATABASE_PATH']=str(Path(scratch)/'company.db')
 import main,create_admin
 with TestClient(main.app) as client:
  assert client.get('/api/health').json()['database']=='sqlite'
  with patch.object(sys,'argv',['create_admin.py','--email','hr@company.example','--name','System Administrator','--code','HR-001','--location','Chennai']),patch.object(create_admin.getpass,'getpass',side_effect=['TestStrongerPassword9876!']*2):
   create_admin.main()
  login=client.post('/api/auth/login',json={'email':'hr@company.example','password':'TestStrongerPassword9876!'})
  assert login.status_code==200,login.text
  h={'Authorization':'Bearer '+login.json()['token']}
  profile=client.get('/api/admin/organization-profile',headers=h)
  assert profile.status_code==200 and profile.json() is None
  init=client.get('/api/admin/setup/overview',headers=h).json()
  assert init['database_engine']=='sqlite' and not next(c['ready'] for c in init['checks'] if c['key']=='mysql')
  company={'name':'Real HRM','legal_name':'Real HRM Solutions Private Limited','country':'India','timezone':'Asia/Kolkata','contact_email':'hr@company.example','website':'https://example.com'}
  r=client.put('/api/admin/organization-profile',json=company,headers=h)
  assert r.status_code==200,r.text
  assert client.get('/api/admin/organization-profile',headers=h).json()['legal_name']==company['legal_name']
  assert client.get('/api/admin/setup/overview',headers=h).json()['completed']>=1
  assert client.put('/api/admin/organization-profile',json={**company,'website':'http://unsafe.com'},headers=h).status_code==422
  dep=client.post('/api/organization/departments',headers=h,json={'name':'Engineering','location':'Chennai'})
  assert dep.status_code in (200,201),dep.text
  rows=[{'code':'SASS-ENG-001','name':'First Employee','email':'staff.one@company.example','designation':'Engineer','department':'Engineering','location':'Chennai','work_mode':'Hybrid','role':'employee','join_date':'2026-01-20'},
        {'code':'SASS-ENG-002','name':'Second Employee','email':'staff.two@company.example','designation':'Engineer','department':'Engineering','location':'Chennai','work_mode':'Remote','role':'manager','join_date':'2026-01-21'}]
  prev=client.post('/api/admin/employees/import/preview',headers=h,json={'records':rows})
  assert prev.status_code==200 and prev.json()['valid']==2,prev.text
  invalid=client.post('/api/admin/employees/import/preview',headers=h,json={'records':[rows[0],{**rows[1],'email':rows[0]['email']}]})
  assert invalid.status_code==200 and invalid.json()['errors'],invalid.text
  count=lambda:len(client.get('/api/employees',headers=h).json())
  before=count()
  rejected=client.post('/api/admin/employees/import/commit',headers=h,json={'records':[rows[0],{**rows[1],'department':'Unknown'}],'confirm':'IMPORT'})
  assert rejected.status_code==422 and count()==before,rejected.text
  result=client.post('/api/admin/employees/import/commit',headers=h,json={'records':rows,'confirm':'IMPORT'})
  assert result.status_code==201 and result.json()['created']==2,result.text
  assert count()==before+2
  with main.db() as conn:
   inactive=conn.execute("SELECT COUNT(*) FROM employees WHERE code IN ('SASS-ENG-001','SASS-ENG-002') AND account_active=0").fetchone()[0]
   audit=conn.execute("SELECT COUNT(*) FROM audit_events WHERE action='employee.imported'").fetchone()[0]
  assert inactive==2 and audit==1
  # Import accounts can be invited despite pending activation, but suspended users cannot.
  import platform_plus
  with patch.object(platform_plus,'send_activation_email') as delivery:
   pending_invite=client.post('/api/admin/invitations',headers=h,json={'employee_id':next(x['id'] for x in client.get('/api/admin/accounts',headers=h).json() if x['email']=='staff.one@company.example')})
  assert pending_invite.status_code==201,pending_invite.text
  assert delivery.call_count==1
  first_id=next(x['id'] for x in client.get('/api/admin/accounts',headers=h).json() if x['email']=='staff.one@company.example')
  suspended=client.patch(f'/api/admin/accounts/{first_id}',headers=h,json={'active':False})
  assert suspended.status_code==200,suspended.text
  assert client.post('/api/admin/invitations',headers=h,json={'employee_id':first_id}).status_code==409
  assert client.patch(f'/api/admin/accounts/{first_id}',headers=h,json={'active':True}).status_code==200
  assert client.post('/api/admin/employees/import/commit',headers=h,json={'records':rows,'confirm':'IMPORT'}).status_code==422
  assert count()==before+2
  # A genuine employee's token must not call administrator setup APIs.
  with main.db() as conn:
   target=conn.execute('SELECT id FROM employees WHERE email=?',('staff.one@company.example',)).fetchone()[0]
   conn.execute('UPDATE employees SET account_active=1,password_hash=? WHERE id=?',(main.hash_password('EmployeeLongPass9876'),target))
  stafflogin=client.post('/api/auth/login',json={'email':'staff.one@company.example','password':'EmployeeLongPass9876'})
  assert stafflogin.status_code==200,stafflogin.text
  eh={'Authorization':'Bearer '+stafflogin.json()['token']}
  assert client.get('/api/admin/setup/overview',headers=eh).status_code==403
  assert client.put('/api/admin/organization-profile',headers=eh,json=company).status_code==403
  assert client.post('/api/admin/employees/import/preview',headers=eh,json={'records':rows}).status_code==403
  assert client.post('/api/admin/employees/import/commit',headers=eh,json={'records':rows,'confirm':'IMPORT'}).status_code==403
  print('PASS: real company profile, startup readiness, CSV preview, duplicate checks, rollback, inactive imports, audit, RBAC')

"""Role-based smoke of every static GET API endpoint against an empty test-only database."""
import os,tempfile,sys
from pathlib import Path
from unittest.mock import patch
os.environ.update(SASS_HRM_TESTING='1',DB_ENGINE='sqlite',JWT_SECRET='audit-only-random-secret-very-long-for-testing-not-real')
from fastapi.testclient import TestClient
with tempfile.TemporaryDirectory() as scratch:
 os.environ['DATABASE_PATH']=str(Path(scratch)/'audit.sqlite')
 import main,create_admin
 with TestClient(main.app) as client:
  with patch.object(sys,'argv',['create_admin.py','--email','hr-admin@company.example','--developer','--name','Test HR','--code','SASS-A-1','--location','India']),patch.object(create_admin.getpass,'getpass',side_effect=['SecurityAuditTestPassword987!']*2):create_admin.main()
  login=client.post('/api/auth/login',json={'email':'hr-admin@company.example','password':'SecurityAuditTestPassword987!'})
  assert login.status_code==200,login.text
  h={'Authorization':'Bearer '+login.json()['token']}
  emp=client.post('/api/employees',headers=h,json={'name':'Audit Tester','email':'audit.user@sass.example','designation':'QA Engineer','department':'Quality','location':'Hyderabad','role':'employee'})
  assert emp.status_code==201,emp.text
  with main.db() as conn:conn.execute('UPDATE employees SET password_hash=?,account_active=1 WHERE id=?',(main.hash_password('EmployeeAuditPassword987!'),emp.json()['id']))
  employee=client.post('/api/auth/login',json={'email':'audit.user@sass.example','password':'EmployeeAuditPassword987!'})
  eh={'Authorization':'Bearer '+employee.json()['token']}
  paths=sorted({r.path for r in main.app.routes if getattr(r,'methods',None) and 'GET' in r.methods and r.path.startswith('/api/') and '{' not in r.path})
  problems=[];count=0
  for path in paths:
   for who,headers in [('admin',h),('employee',eh)]:
    result=client.get(path,headers=headers);count+=1
    if result.status_code>=500 or result.status_code not in (200,401,403,404,422): problems.append((who,path,result.status_code,result.text[:180]))
  assert not problems,problems
  print('PASS static GET audit: '+str(count)+' role-scoped calls across '+str(len(paths))+' endpoints (any expected 403 is permitted)')

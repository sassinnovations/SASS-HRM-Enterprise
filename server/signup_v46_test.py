"""Public sign-up and admin-reviewed provisioning regression test (SQLite isolation)."""
import os, sys, tempfile
from pathlib import Path
from unittest.mock import patch

os.environ['SASS_HRM_TESTING']='1'
os.environ['DB_ENGINE']='sqlite'
os.environ['JWT_SECRET']='LOCAL-ONLY-v46-automated-tests-an-isolated-signup-secret'
from fastapi.testclient import TestClient

with tempfile.TemporaryDirectory() as folder:
 os.environ['DATABASE_PATH']=str(Path(folder)/'signup-test.db')
 import main, create_admin
 with TestClient(main.app) as client:
  with patch.object(sys,'argv',['create_admin.py','--email','owner@example.org','--name','Owner','--code','SASS-ADMIN-1','--location','HYD']),patch.object(create_admin.getpass,'getpass',side_effect=['AdminStrongPass123!']*2):
   create_admin.main()
  login=lambda email,password:client.post('/api/auth/login',json={'email':email,'password':password})
  result=login('owner@example.org','AdminStrongPass123!')
  assert result.status_code==200,result.text
  admin={'Authorization':'Bearer '+result.json()['token']}
  # Administrator-only policy settings persist in the real database and control the public form.
  initial=client.get('/api/auth/signup-settings')
  assert initial.status_code==200 and set(initial.json()['allowed_roles'])=={'employee','hr_subadmin','admin'},initial.text
  assert client.get('/api/admin/signup-settings').status_code==401
  assert client.put('/api/admin/signup-settings',json={'enabled':False,'allow_employee':True,'allow_hr_subadmin':True,'allow_admin':True,'allowed_email_domain':''}).status_code==401
  policy={'enabled':False,'allow_employee':True,'allow_hr_subadmin':True,'allow_admin':True,'allowed_email_domain':''}
  result=client.put('/api/admin/signup-settings',json=policy,headers=admin)
  assert result.status_code==200,result.text
  assert client.get('/api/auth/signup-settings').json()['allowed_roles']==[]
  with main.db() as conn:
   assert conn.execute('SELECT enabled FROM account_signup_settings WHERE id=1').fetchone()['enabled']==0
  assert client.post('/api/auth/signup-requests',json={'name':'Closed Applicant','email':'closed@example.org','work_email':'closed@example.org','role':'employee','designation':'Employee','department':'HR','location':'HYD','work_mode':'Hybrid','password':'Strong123456789!'}).status_code==403
  result=client.put('/api/admin/signup-settings',json={**policy,'enabled':True,'allow_admin':False,'allowed_email_domain':'example.org'},headers=admin)
  assert result.status_code==200,result.text
  assert client.get('/api/auth/signup-settings').json()['allowed_roles']==['employee','hr_subadmin']
  blocked={'name':'Blocked Applicant','email':'blocked@example.org','role':'admin','designation':'Analyst','department':'HR','location':'HYD','work_mode':'Hybrid','password':'Safe1234567890!', 'work_email':'blocked@example.org'}
  assert client.post('/api/auth/signup-requests',json=blocked).status_code==403
  assert client.post('/api/auth/signup-requests',json={**blocked,'role':'employee','email':'blocked@outsider.com','work_email':'blocked@outsider.com'}).status_code==422
  # Restore policy so the rest of the test exercises every role.
  assert client.put('/api/admin/signup-settings',json={**policy,'enabled':True},headers=admin).status_code==200
  data={'name':'New Applicant','email':'Applicant@example.org','work_email':'work.applicant@example.org','role':'admin','designation':'New Employee','department':'HR','location':'HYD','work_mode':'Hybrid','password':'SolidApplicant123!'}
  noauth=client.get('/api/admin/signup-requests')
  assert noauth.status_code==401
  bad=client.post('/api/auth/signup-requests',json={**data,'password':'unsafe'})
  assert bad.status_code==422,bad.text
  req=client.post('/api/auth/signup-requests',json=data)
  assert req.status_code==202,req.text
  assert not any(x in str(req.json()) for x in ('SolidApplicant123!','password_hash'))
  assert login(data['email'],data['password']).status_code==401,'Public admin signup must never log in immediately'
  repeated=client.post('/api/auth/signup-requests',json=data)
  assert repeated.status_code==202 and repeated.json()==req.json()
  with main.db() as conn:
   existing=conn.execute("SELECT * FROM account_signup_requests WHERE email=?",('applicant@example.org',)).fetchall()
   assert len(existing)==1
   assert existing[0]['status']=='Pending' and 'SolidApplicant123!' not in existing[0]['password_hash']
  items=client.get('/api/admin/signup-requests',headers=admin)
  assert items.status_code==200,items.text
  assert len(items.json())==1 and 'password_hash' not in items.text and 'SolidApplicant123!' not in items.text
  rid=items.json()[0]['id']
  assert client.post(f'/api/admin/signup-requests/{rid}/review',json={'decision':'Approved','identity_verified':True,'review_note':'Verified via HR manager in person'}).status_code==401
  assert client.post(f'/api/admin/signup-requests/{rid}/review',json={'decision':'Approved','identity_verified':False},headers=admin).status_code==422
  assert client.post(f'/api/admin/signup-requests/{rid}/review',json={'decision':'Approved','identity_verified':True},headers=admin).status_code==422
  reviewed=client.post(f'/api/admin/signup-requests/{rid}/review',json={'decision':'Approved','identity_verified':True,'review_note':'Verified via HR manager in person'},headers=admin)
  assert reviewed.status_code==200,reviewed.text
  assert client.post(f'/api/admin/signup-requests/{rid}/review',json={'decision':'Approved','identity_verified':True,'review_note':'Verified via HR manager in person'},headers=admin).status_code==409
  user=login(data['work_email'],data['password'])
  assert user.status_code==200,user.text
  assert user.json()['user']['role']=='admin','Privileged roles only from administrator approval'
  assert login(data['email'],data['password']).status_code==200
  with main.db() as conn:
   item=conn.execute('SELECT password_hash,status,employee_id FROM account_signup_requests WHERE id=?',(rid,)).fetchone()
   assert item['status']=='Approved' and item['password_hash']=='REDACTED'
   emp=conn.execute('SELECT role,password_hash,work_email,code FROM employees WHERE id=?',(item['employee_id'],)).fetchone()
   assert emp['role']=='admin' and emp['code'].startswith('SASS-') and emp['work_email']=='work.applicant@example.org'
   assert 'SolidApplicant123!' not in emp['password_hash']
  # Rejection never provisions an account, sensitive request credentials are cleared.
  other={**data,'name':'Reject Applicant','email':'reject@example.org','work_email':'reject@example.org','role':'hr_subadmin'}
  assert client.post('/api/auth/signup-requests',json=other).status_code==202
  pending=client.get('/api/admin/signup-requests',headers=admin).json()
  assert len(pending)==1
  other_id=pending[0]['id']
  reject=client.post(f'/api/admin/signup-requests/{other_id}/review',json={'decision':'Rejected','identity_verified':True,'review_note':'Verified via HR manager in person'},headers=admin)
  assert reject.status_code==200,reject.text
  assert login('reject@example.org',data['password']).status_code==401
  with main.db() as conn:
   reject_row=conn.execute('SELECT status,password_hash FROM account_signup_requests WHERE id=?',(other_id,)).fetchone()
   assert reject_row['status']=='Rejected' and reject_row['password_hash']=='REDACTED'
  # Manager cannot approve or enumerate requests.
  employee={**data,'name':'Employee','email':'employee-v46@example.org','work_email':'employee-v46@example.org','role':'employee'}
  assert client.post('/api/auth/signup-requests',json=employee).status_code==202
  pending=client.get('/api/admin/signup-requests',headers=admin).json()[0]
  assert client.post(f'/api/admin/signup-requests/{pending["id"]}/review',json={'decision':'Approved','identity_verified':True,'review_note':'Verified via HR manager in person'},headers=admin).status_code==200
  staff=login('employee-v46@example.org',data['password'])
  staff_head={'Authorization':'Bearer '+staff.json()['token']}
  assert client.get('/api/admin/signup-requests',headers=staff_head).status_code==403
  assert client.post(f'/api/admin/signup-requests/{pending["id"]}/review',json={'decision':'Rejected','identity_verified':True,'review_note':'Verified via HR manager in person'},headers=staff_head).status_code==403
  # Admin requests with an existing sign-in email produce the same public acknowledgement.
  again=client.post('/api/auth/signup-requests',json=data)
  assert again.status_code==202 and again.json()==req.json()
  # Restricted HR Sub-Admin can log in but cannot approve signups.
  subordinate={**data,'name':'HR Sub-Admin','email':'subadmin@example.org','work_email':'subadmin@example.org','role':'hr_subadmin'}
  assert client.post('/api/auth/signup-requests',json=subordinate).status_code==202
  rid_sub=client.get('/api/admin/signup-requests',headers=admin).json()[0]['id']
  assert client.post(f'/api/admin/signup-requests/{rid_sub}/review',json={'decision':'Approved','identity_verified':True},headers=admin).status_code==200
  hr=login('subadmin@example.org',data['password'])
  assert hr.status_code==200 and hr.json()['user']['role']=='manager'
  hr_header={'Authorization':'Bearer '+hr.json()['token']}
  assert client.get('/api/admin/signup-settings',headers=hr_header).status_code==403
  assert client.put('/api/admin/signup-settings',json=policy,headers=hr_header).status_code==403
  # Old pending applications are expired and redacted, allowing a fresh request.
  stale={**data,'name':'Stale Applicant','email':'stale@example.org','work_email':'stale@example.org','role':'employee'}
  assert client.post('/api/auth/signup-requests',json=stale).status_code==202
  with main.db() as conn:
   conn.execute("UPDATE account_signup_requests SET created_at='2025-01-01T00:00:00+00:00' WHERE email='stale@example.org'")
  assert client.post('/api/auth/signup-requests',json=stale).status_code==202
  with main.db() as conn:
   entries=conn.execute('SELECT status,password_hash FROM account_signup_requests WHERE email=? ORDER BY id',('stale@example.org',)).fetchall()
   assert len(entries)==2 and entries[0]['status']=='Expired' and entries[0]['password_hash']=='REDACTED' and entries[1]['status']=='Pending'
  assert len(client.get('/api/admin/signup-requests?status=Expired',headers=admin).json())==1
  with TestClient(main.app) as new_client:
   assert new_client.post('/api/auth/login',json={'email':'employee-v46@example.org','password':data['password']}).status_code==200
  print('PASS v4.6 extended public signup pending / approval / rejection / login persistence / access privacy')

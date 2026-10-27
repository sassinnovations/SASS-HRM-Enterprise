"""Isolated v3.9 performance suite regressions, no employee production data."""
import os,tempfile
from pathlib import Path
from datetime import date,timedelta
from fastapi.testclient import TestClient
os.environ.update(SASS_HRM_TESTING='1',DB_ENGINE='sqlite',JWT_SECRET='test-v39-performance-isolation-secret-0123456789-ABCDE')
with tempfile.TemporaryDirectory() as work:
 os.environ['DATABASE_PATH']=str(Path(work)/'performance.sqlite')
 import main
 with TestClient(main.app) as c:
  users={}
  for name,role in [('HR','admin'),('Manager','manager'),('OtherManager','manager'),('Alice','employee'),('Bob','employee')]:
   with main.db() as db:
    record=db.execute('INSERT INTO employees(code,name,email,role,designation,department,location,join_date,password_hash,account_active) VALUES(?,?,?,?,?,?,?,?,?,1)',
       (name.upper(),name,name.lower()+'@example.invalid',role,'Developer','Engineering','Hyderabad',date.today().isoformat(),main.hash_password('Strong-test-only-passphrase-42')))
    users[name]=record.lastrowid
  with main.db() as db:
   db.execute('UPDATE employees SET manager_id=? WHERE id=?',(users['Manager'],users['Alice']))
   db.execute('UPDATE employees SET manager_id=? WHERE id=?',(users['OtherManager'],users['Bob']))
  def h(name):
   response=c.post('/api/auth/login',json={'email':name.lower()+'@example.invalid','password':'Strong-test-only-passphrase-42'})
   assert response.status_code==200,response.text
   return {'Authorization':'Bearer '+response.json()['token']}
  hr,manager,other,alice,bob=[h(k) for k in ['HR','Manager','OtherManager','Alice','Bob']]
  endpoint='/api/performance-v2'
  today=date.today()
  add_days=lambda n:(today+timedelta(days=n)).isoformat()
  body={'name':'Annual Test Cycle','starts_on':add_days(-1),'self_due_on':add_days(3),'manager_due_on':add_days(9),'ends_on':add_days(20)}
  assert c.get(endpoint+'/cycles').status_code==401
  for headers in (manager,alice,bob):
   assert c.post(endpoint+'/cycles',json=body,headers=headers).status_code==403
  assert c.post(endpoint+'/cycles',json={**body,'self_due_on':add_days(30)},headers=hr).status_code==422
  create=c.post(endpoint+'/cycles',json=body,headers=hr);assert create.status_code==201,create.text
  cycle_id=create.json()['id']
  assert c.post(endpoint+'/cycles',json=body,headers=hr).status_code==409
  self_body={'cycle_id':cycle_id,'summary':'Delivered several customer-facing features this quarter.',
    'strengths':'Clear communication','growth':'Improve architecture design'}
  assert c.post(endpoint+'/appraisals',headers=alice,json=self_body).status_code==409
  assert c.patch(endpoint+f'/cycles/{cycle_id}',headers=manager,json={'status':'Open'}).status_code==403
  assert c.patch(endpoint+f'/cycles/{cycle_id}',headers=hr,json={'status':'Open'}).status_code==200
  assert c.patch(endpoint+f'/cycles/{cycle_id}',headers=hr,json={'status':'Draft'}).status_code==409
  submit=c.post(endpoint+'/appraisals',headers=alice,json=self_body);assert submit.status_code==201,submit.text
  app_id=submit.json()['id']
  assert c.post(endpoint+'/appraisals',headers=alice,json=self_body).status_code==409
  assert c.post(endpoint+'/appraisals',headers=bob,json={**self_body,'summary':'I worked on my assigned development tasks.'}).status_code==201
  assert len(c.get(endpoint+'/appraisals',headers=alice).json())==1
  assert len(c.get(endpoint+'/appraisals',headers=bob).json())==1
  assert len(c.get(endpoint+'/appraisals',headers=manager).json())==1
  assert len(c.get(endpoint+'/appraisals',headers=other).json())==1
  assert len(c.get(endpoint+'/appraisals',headers=hr).json())==2
  review={'summary':'Delivered agreed milestones, with scope for improvement.','strengths':'Collaboration','growth':'Review priorities weekly','rating':4}
  assert c.post(endpoint+f'/appraisals/{app_id}/manager-review',headers=alice,json=review).status_code==403
  assert c.post(endpoint+f'/appraisals/{app_id}/manager-review',headers=other,json=review).status_code==403
  assert c.post(endpoint+f'/appraisals/{app_id}/manager-review',headers=manager,json={**review,'rating':6}).status_code==422
  done=c.post(endpoint+f'/appraisals/{app_id}/manager-review',headers=manager,json=review);assert done.status_code==200,done.text
  assert c.post(endpoint+f'/appraisals/{app_id}/manager-review',headers=manager,json=review).status_code==409
  assert c.post(endpoint+f'/appraisals/{app_id}/acknowledge',headers=bob).status_code==403
  assert c.post(endpoint+f'/appraisals/{app_id}/acknowledge',headers=manager).status_code==403
  assert c.post(endpoint+f'/appraisals/{app_id}/acknowledge',headers=alice).status_code==200
  assert c.post(endpoint+f'/appraisals/{app_id}/acknowledge',headers=alice).status_code==409
  check={'employee_id':users['Alice'],'meeting_on':add_days(1),'discussion':'Reviewed project milestones and feedback.','action_items':'Document next steps'}
  assert c.post(endpoint+'/checkins',headers=alice,json=check).status_code==403
  assert c.post(endpoint+'/checkins',headers=other,json=check).status_code==403
  assert c.post(endpoint+'/checkins',headers=manager,json={**check,'employee_id':users['Bob']}).status_code==403
  meeting=c.post(endpoint+'/checkins',headers=manager,json=check);assert meeting.status_code==201,meeting.text
  assert len(c.get(endpoint+'/checkins',headers=alice).json())==1
  assert len(c.get(endpoint+'/checkins',headers=bob).json())==0
  assert len(c.get(endpoint+'/checkins',headers=other).json())==0
  assert len(c.get(endpoint+'/checkins',headers=manager).json())==1
  assert c.patch(endpoint+f'/cycles/{cycle_id}',headers=hr,json={'status':'Closed'}).status_code==200
  assert c.patch(endpoint+f'/cycles/{cycle_id}',headers=hr,json={'status':'Open'}).status_code==409
  assert c.post(endpoint+'/appraisals',headers=alice,json=self_body).status_code==409
  with main.db() as db:
   record=db.execute('SELECT manager_rating,acknowledged_at FROM performance_appraisals WHERE id=?',(app_id,)).fetchone()
   assert record['manager_rating']==4 and record['acknowledged_at']
   actions=[r['action'] for r in db.execute("SELECT action FROM audit_events WHERE action LIKE 'performance.%'")]
   assert len(actions)>=7,actions
 print('PASS v3.9 performance: isolation, role guards, cycles, self-review, manager-review, acknowledgement, check-ins, audit')

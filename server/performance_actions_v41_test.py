"""Isolated permission and lifecycle checks for v4.1 performance follow-ups."""
import os,tempfile
from datetime import date,timedelta
from pathlib import Path
from fastapi.testclient import TestClient
os.environ.update(SASS_HRM_TESTING='1',DB_ENGINE='sqlite',JWT_SECRET='test-v41-secret-for-performance-actions-123456789')
with tempfile.TemporaryDirectory() as directory:
 os.environ['DATABASE_PATH']=str(Path(directory)/'test.sqlite')
 import main
 with TestClient(main.app) as client:
  ids={}
  for name,role in [('HR','admin'),('Manager','manager'),('Elsewhere','manager'),('Alice','employee'),('Bob','employee')]:
   with main.db() as c:
    out=c.execute('INSERT INTO employees(code,name,email,role,designation,department,location,join_date,password_hash,account_active) VALUES(?,?,?,?,?,?,?,?,?,1)',(name.upper(),name,name.lower()+'@example.invalid',role,'Engineer','Research','Main',str(date.today()),main.hash_password('TestOnlyGoodPassword123')))
    ids[name]=out.lastrowid
  with main.db() as c:
   c.execute('UPDATE employees SET manager_id=? WHERE id=?',(ids['Manager'],ids['Alice']))
   c.execute('UPDATE employees SET manager_id=? WHERE id=?',(ids['Elsewhere'],ids['Bob']))
  def h(name):
   r=client.post('/api/auth/login',json={'email':name.lower()+'@example.invalid','password':'TestOnlyGoodPassword123'})
   assert r.status_code==200,r.text
   return {'Authorization':'Bearer '+r.json()['token']}
  admin,manager,other,alice,bob=[h(v) for v in ('HR','Manager','Elsewhere','Alice','Bob')]
  url='/api/performance-followups'
  today=str(date.today());later=str(date.today()+timedelta(days=8))
  payload={'employee_id':ids['Alice'],'title':'Document the agreed workshop plan','notes':'Prepare a summary of training topics.','category':'1:1 meeting','due_on':later}
  assert client.get(url+'/actions').status_code==401
  assert client.post(url+'/actions',json=payload).status_code==401
  assert client.post(url+'/actions',headers=bob,json=payload).status_code==403
  assert client.post(url+'/actions',headers=other,json=payload).status_code==403
  assert client.post(url+'/actions',headers=alice,json={**payload,'due_on':str(date.today()-timedelta(days=1))}).status_code==422
  created=client.post(url+'/actions',headers=manager,json=payload)
  assert created.status_code==201,created.text
  aid=created.json()['id']
  assert len(client.get(url+'/actions',headers=admin).json())==1
  assert len(client.get(url+'/actions',headers=manager).json())==1
  assert len(client.get(url+'/actions',headers=alice).json())==1
  assert client.get(url+'/actions',headers=bob).json()==[]
  assert client.get(url+'/actions',headers=other).json()==[]
  assert client.patch(url+f'/actions/{aid}',headers=bob,json={'status':'Completed'}).status_code==403
  assert client.patch(url+f'/actions/{aid}',headers=alice,json={'status':'Completed'}).status_code==200
  assert client.patch(url+f'/actions/{aid}',headers=manager,json={'status':'Completed'}).status_code==409
  assert len(client.get(url+'/actions',headers=alice,params={'status':'Completed'}).json())==1
  assert client.patch(url+f'/actions/{aid}',headers=manager,json={'status':'Open'}).status_code==200
  assert client.patch(url+f'/actions/{aid}',headers=alice,json={'status':'Cancelled'}).status_code==200
  assert client.patch(url+f'/actions/{aid}',headers=alice,json={'status':'Open'}).status_code==409
  with main.db() as c:
   c.execute("INSERT INTO performance_review_cycles(name,starts_on,ends_on,self_due_on,manager_due_on,status,created_by,created_at) VALUES(?,?,?,?,?,?,?,?)",('Fall 2026',today,later,today,later,'Open',ids['HR'],today))
   cid=c.execute('SELECT id FROM performance_review_cycles').fetchone()['id']
   c.execute('INSERT INTO performance_appraisals(cycle_id,employee_id,self_summary,self_strengths,self_growth,self_submitted_at) VALUES(?,?,?,?,?,?)',(cid,ids['Alice'],'Summary','Strengths','Growth',today))
  mine=client.get(url+'/progress',headers=alice)
  assert mine.status_code==200,mine.text
  assert mine.json()['cycles'][0]['eligible_employees']==1
  assert mine.json()['cycles'][0]['submitted_assessments']==1
  assert client.get(url+'/progress',headers=bob).json()['cycles'][0]['submitted_assessments']==0
  assert client.get(url+'/progress',headers=manager).json()['cycles'][0]['submitted_assessments']==1
  assert client.get(url+'/progress',headers=admin).json()['cycles'][0]['eligible_employees']==5
  with main.db() as c:
   c.execute('UPDATE employees SET manager_id=? WHERE id=?',(ids['Elsewhere'],ids['Alice']))
  assert client.get(url+'/actions',headers=manager).json()==[]
  assert len(client.get(url+'/actions',headers=other).json())==1
  assert client.patch(url+f'/actions/{aid}',headers=manager,json={'status':'Completed'}).status_code==403
  with main.db() as c:
   actions=[x['action'] for x in c.execute("SELECT action FROM audit_events WHERE action LIKE 'performance.followup.%'")]
   assert len(actions)>=4,actions
 print('PASS v4.1 scoped follow-up actions, review progress, manager changes, audit, validation and authentication')

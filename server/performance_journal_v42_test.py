"""Isolated privacy, cross-team, visibility and append-only performance records."""
import os,tempfile
from pathlib import Path
from datetime import date,timedelta
from fastapi.testclient import TestClient
os.environ.update(SASS_HRM_TESTING='1',DB_ENGINE='sqlite',JWT_SECRET='test-v42-secret-for-isolated-security-123456789')
with tempfile.TemporaryDirectory() as tmp:
 os.environ['DATABASE_PATH']=str(Path(tmp)/'db.sqlite')
 import main
 with TestClient(main.app) as client:
  ids={}
  for name,role in [('Admin','admin'),('Manager','manager'),('OtherManager','manager'),('Alice','employee'),('Bob','employee')]:
   with main.db() as c:
    record=c.execute('INSERT INTO employees(code,name,email,role,designation,department,location,join_date,password_hash,account_active) VALUES(?,?,?,?,?,?,?,?,?,1)',(name.upper(),name,name.lower()+'@example.invalid',role,'Engineer','Research','Hyderabad',str(date.today()),main.hash_password('StrongTestPass12345')))
    ids[name]=record.lastrowid
  with main.db() as c:
   c.execute('UPDATE employees SET manager_id=? WHERE id=?',(ids['Manager'],ids['Alice']))
   c.execute('UPDATE employees SET manager_id=? WHERE id=?',(ids['OtherManager'],ids['Bob']))
   for n in ('Alice','Bob'):
    c.execute('INSERT INTO goals(employee_id,title,description,due_date) VALUES(?,?,?,?)',(ids[n],f'{n} quarterly quality goal','Complete the team objective',str(date.today()+timedelta(days=15))))
  def auth(n):
   r=client.post('/api/auth/login',json={'email':n.lower()+'@example.invalid','password':'StrongTestPass12345'})
   assert r.status_code==200,r.text
   return {'Authorization':'Bearer '+r.json()['token']}
  admin,manager,other,alice,bob=[auth(n) for n in ('Admin','Manager','OtherManager','Alice','Bob')]
  pref='/api/performance-journal'
  payload={'title':'Migrated reporting flow','details':'Reduced manual checks through documentation','category':'Project','occurred_on':str(date.today()),'visibility':'Private'}
  assert client.get(pref+'/evidence').status_code==401
  assert client.post(pref+'/evidence',json=payload).status_code==401
  bad=client.post(pref+'/evidence',json={**payload,'occurred_on':str(date.today()+timedelta(days=1))},headers=alice)
  assert bad.status_code==422
  made=client.post(pref+'/evidence',json=payload,headers=alice)
  assert made.status_code==201,made.text
  eid=made.json()['id']
  assert len(client.get(pref+'/evidence',headers=alice).json())==1
  for h in (manager,other,admin,bob): assert client.get(pref+'/evidence',headers=h).json()==[]
  assert client.patch(pref+f'/evidence/{eid}',json={'visibility':'Shared'},headers=bob).status_code==403
  assert client.patch(pref+f'/evidence/{eid}',json={'visibility':'Shared'},headers=alice).status_code==200
  assert len(client.get(pref+'/evidence',headers=manager).json())==1
  assert len(client.get(pref+'/evidence',headers=admin).json())==1
  assert client.get(pref+'/evidence',headers=other).json()==[]
  with main.db() as c:c.execute('UPDATE employees SET manager_id=? WHERE id=?',(ids['OtherManager'],ids['Alice']))
  assert client.get(pref+'/evidence',headers=manager).json()==[]
  assert len(client.get(pref+'/evidence',headers=other).json())==1
  assert client.patch(pref+f'/evidence/{eid}',json={'archived':True},headers=alice).status_code==200
  assert client.get(pref+'/evidence',headers=other,params={'include_archived':'true'}).json()==[]
  assert client.get(pref+'/evidence',headers=admin,params={'include_archived':'true'}).json()==[]
  assert len(client.get(pref+'/evidence',headers=alice,params={'include_archived':'true'}).json())==1
  assert client.patch(pref+f'/evidence/{eid}',json={'archived':False,'visibility':'Private'},headers=alice).status_code==200
  with main.db() as c:goal_a=c.execute('SELECT id FROM goals WHERE employee_id=?',(ids['Alice'],)).fetchone()['id'];goal_b=c.execute('SELECT id FROM goals WHERE employee_id=?',(ids['Bob'],)).fetchone()['id']
  checkin={'goal_id':goal_a,'summary':'Completed draft documentation and submitted review','blockers':'Awaiting validation','next_step':'Present results at meeting'}
  assert client.post(pref+'/checkins',json={**checkin,'goal_id':goal_b},headers=alice).status_code==403
  assert client.post(pref+'/checkins',json=checkin,headers=manager).status_code==403 # manager relationship changed
  created=client.post(pref+'/checkins',json=checkin,headers=alice)
  assert created.status_code==201,created.text
  assert len(client.get(pref+'/checkins',headers=alice).json())==1
  assert client.get(pref+'/checkins',headers=manager).json()==[]
  assert len(client.get(pref+'/checkins',headers=other).json())==1
  assert client.get(pref+'/checkins',headers=bob).json()==[]
  assert client.get(pref+'/checkins',headers=bob,params={'goal_id':goal_a}).status_code==403
  assert len(client.get(pref+'/checkins',headers=admin).json())==1
  with main.db() as c:
   actions=[x['action'] for x in c.execute("SELECT action FROM audit_events WHERE action LIKE 'performance.%'")]
   assert 'performance.evidence.created' in actions and 'performance.goal_checkin.created' in actions
 print('PASS v4.2 evidence privacy, manager changes, archived visibility, authentication, goal journal, validation and audits')

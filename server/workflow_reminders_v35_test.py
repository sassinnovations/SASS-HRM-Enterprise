"""Isolated v3.5 workflow reminders test. Uses a disposable SQLite database."""
import os
import tempfile
from datetime import date, timedelta
from pathlib import Path
from fastapi.testclient import TestClient
os.environ.update(SASS_HRM_TESTING='1',DB_ENGINE='sqlite',JWT_SECRET='isolated-v35-deadline-test-secret-longer-than-40-characters')
with tempfile.TemporaryDirectory() as temp:
    os.environ['DATABASE_PATH']=str(Path(temp)/'test.db')
    import main
    with TestClient(main.app) as client:
        with main.db() as c:
            ids={}
            for code,name,role,active in [('ADMIN','Admin','admin',1),('ONE','One','employee',1),('TWO','Two','employee',1),('OFF','Inactive','employee',0)]:
                r=c.execute('''INSERT INTO employees(code,name,email,role,designation,department,location,join_date,password_hash,account_active)
                    VALUES(?,?,?,?,?,?,?,?,?,?)''',(code,name,code.lower()+'@example.invalid',role,'Test','Operations','HQ',date.today().isoformat(),main.hash_password('Example-Password-12345'),active))
                ids[code]=r.lastrowid
            before=(date.today()-timedelta(days=2)).isoformat()
            future=(date.today()+timedelta(days=1)).isoformat()
            far=(date.today()+timedelta(days=100)).isoformat()
            c.execute('INSERT INTO hr_tasks(title,assignee_id,created_by,due_date,status,created_at) VALUES(?,?,?,?,?,?)',('Quarterly status',ids['ONE'],ids['ADMIN'],before,'Open',before))
            c.execute('INSERT INTO hr_tasks(title,assignee_id,created_by,due_date,status,created_at) VALUES(?,?,?,?,?,?)',('Distant task',ids['ONE'],ids['ADMIN'],far,'Open',before))
            c.execute('INSERT INTO hr_tasks(title,assignee_id,created_by,due_date,status,created_at) VALUES(?,?,?,?,?,?)',('Private assignment',ids['TWO'],ids['ADMIN'],future,'Open',before))
            c.execute('INSERT INTO hr_tasks(title,assignee_id,created_by,due_date,status,created_at) VALUES(?,?,?,?,?,?)',('Inactive assignment',ids['OFF'],ids['ADMIN'],before,'Open',before))
            c.execute('INSERT INTO hr_tasks(title,assignee_id,created_by,due_date,status,created_at) VALUES(?,?,?,?,?,?)',('Closed assignment',ids['ONE'],ids['ADMIN'],before,'Completed',before))
            c.execute('INSERT INTO onboarding(employee_id,title,due_date,status) VALUES(?,?,?,?)',(ids['ONE'],'Complete orientation',future,'Pending'))
            c.execute('INSERT INTO tickets(employee_id,subject,category,description,status,priority,created_at) VALUES(?,?,?,?,?,?,?)',(ids['TWO'],'VPN access','IT','VPN not working','Open','Normal',before))
            ticket_id=c.execute('SELECT id FROM tickets').fetchone()['id']
            c.execute('INSERT INTO ticket_assignments(ticket_id,assignee_id,due_date,updated_at) VALUES(?,?,?,?)',(ticket_id,ids['ADMIN'],before,before))
        def login(code):
            r=client.post('/api/auth/login',json={'email':code.lower()+'@example.invalid','password':'Example-Password-12345'})
            assert r.status_code==200,r.text
            return {'Authorization':'Bearer '+r.json()['token']}
        admin=login('ADMIN');one=login('ONE');two=login('TWO')
        assert client.get('/api/workflow/reminders').status_code==401
        assert client.get('/api/workflow/reminders?status=no',headers=one).status_code==422
        assert client.get('/api/workflow/reminders?limit=9999',headers=one).status_code==422
        own=client.get('/api/workflow/reminders',headers=one)
        assert own.status_code==200,own.text
        assert own.json()['scope']=='personal'
        assert {x['title'] for x in own.json()['items']}=={'Quarterly status','Complete orientation'},own.json()
        assert client.get('/api/workflow/reminders?status=overdue',headers=one).json()['total']==1
        assert {x['title'] for x in client.get('/api/workflow/reminders',headers=two).json()['items']}=={'Private assignment'}
        all_items=client.get('/api/workflow/reminders',headers=admin).json()
        assert all_items['scope']=='organization' and all_items['total']==4,all_items
        assert client.post('/api/workflow/reminders/dispatch',headers=one,json={}).status_code==403
        assert client.post('/api/workflow/reminders/dispatch',headers=admin,json={'max_items':0}).status_code==422
        assert client.post('/api/workflow/reminders/dispatch',headers=admin,json={'kind':'task'}).status_code==422
        assert client.post('/api/workflow/reminders/dispatch',headers=admin,json={'kind':'task','record_id':99999}).status_code==404
        sent=client.post('/api/workflow/reminders/dispatch',headers=admin,json={'max_items':100})
        assert sent.status_code==200,sent.text
        assert sent.json()['sent']==4,sent.json()
        again=client.post('/api/workflow/reminders/dispatch',headers=admin,json={'max_items':100}).json()
        assert again['sent']==0 and again['already_sent_today']==4,again
        targeted=client.post('/api/workflow/reminders/dispatch',headers=admin,json={'max_items':1,'kind':'task','record_id':1}).json()
        assert targeted['sent']==0 and targeted['already_sent_today']==1,targeted
        with main.db() as c:
            r=c.execute('SELECT employee_id,COUNT(*) AS n FROM notifications GROUP BY employee_id').fetchall()
            assert {x['employee_id']:x['n'] for x in r}=={ids['ONE']:2,ids['TWO']:1,ids['ADMIN']:1},r
            assert c.execute('SELECT COUNT(*) AS n FROM workflow_reminder_dispatches').fetchone()['n']==4
            assert c.execute("SELECT COUNT(*) AS n FROM audit_events WHERE action='workflow.reminders.dispatched'").fetchone()['n']==3
            assert c.execute('SELECT COUNT(*) AS n FROM notifications WHERE employee_id=?',(ids['OFF'],)).fetchone()['n']==0
        assert client.get('/api/workflow/reminders',headers=admin).json()['items'][0]['sent_today']
        assert client.get('/api/workspace/inbox',headers=one).json()['unread_count']==2
    print('PASS v3.5: scoped reminder preview, filters, only-admin send, dedup, inactive exclusion, audit, MySQL-schema-compatible SQL')

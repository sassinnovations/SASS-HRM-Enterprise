"""Role-scope and saved-search regression, no production DB or credentials used."""
import os
import tempfile
from pathlib import Path
from datetime import date
from fastapi.testclient import TestClient
os.environ.update(SASS_HRM_TESTING='1', DB_ENGINE='sqlite',
                  JWT_SECRET='isolated-search-testing-secret-example-long-enough-009988776655')
with tempfile.TemporaryDirectory() as folder:
    os.environ['DATABASE_PATH'] = str(Path(folder) / 'search.sqlite')
    import main
    with TestClient(main.app) as client:
        with main.db() as conn:
            ids = {}
            for name, role, manager, dept in [('Admin','admin',None,'HR'),
                ('Manager','manager',None,'Engineering'),('Alice','employee','Manager','Engineering'),
                ('Bob','employee',None,'Finance'),('Cora','employee','Manager','Engineering')]:
                result=conn.execute('''INSERT INTO employees(code,name,email,role,designation,department,
                   location,join_date,password_hash,manager_id,account_active)
                   VALUES(?,?,?,?,?,?,?,?,?,?,1)''', (name.upper(),name+' Name',name.lower()+'@example.invalid',
                   role,'Analyst',dept,'Hyderabad',date.today().isoformat(),
                   main.hash_password('Safe-Example-Pass-012345'),ids.get(manager)))
                ids[name] = result.lastrowid
            conn.execute('INSERT INTO policies(title,category,content,last_updated) VALUES(?,?,?,?)',
                         ('Safety Guide','General','Sensitive source body',date.today().isoformat()))
            conn.execute('INSERT INTO candidates(name,job_title,stage,source,applied_at) VALUES(?,?,?,?,?)',
                         ('Candidate Xavier','Engineer','Interview','Portal',date.today().isoformat()))
            for name in ('Alice','Bob'):
                conn.execute('''INSERT INTO leave_requests(employee_id,start_date,end_date,leave_type,reason,days,status,created_at)
                             VALUES(?,?,?,?,?,?,?,?)''', (ids[name], '2026-11-01','2026-11-02','Special Leave',
                             f'{name} medical confidential secret',2,'Pending','2026-10-22'))
                conn.execute('''INSERT INTO tickets(employee_id,subject,category,description,status,created_at)
                             VALUES(?,?,?,?,?,?)''', (ids[name],f'{name} payroll help','Payroll',
                             'Confidential private ticket message', 'Open','2026-10-22'))
                conn.execute('''INSERT INTO expenses(employee_id,title,amount,category,status,created_at)
                             VALUES(?,?,?,?,?,?)''', (ids[name],f'{name} travel claim',90,'Travel','Pending','2026-10-22'))
            conn.execute('''INSERT INTO hr_tasks(title,assignee_id,created_by,due_date,status,created_at)
                           VALUES(?,?,?,?,?,?)''',('Prepare release',ids['Alice'],ids['Manager'],'2026-11-05','Open','2026-10-22'))
            conn.execute('INSERT INTO policies(title,category,content,last_updated) VALUES(?,?,?,?)',
                         ('SQL 100% manual','IT','No sensitive content','2026-10-22'))
        def login(name):
            r=client.post('/api/auth/login',json={'email':name.lower()+'@example.invalid',
                                                   'password':'Safe-Example-Pass-012345'})
            assert r.status_code==200,r.text
            return {'Authorization':'Bearer '+r.json()['token']}
        admin=login('Admin');manager=login('Manager');alice=login('Alice');bob=login('Bob')
        assert client.get('/api/search/records?q=guide').status_code==401
        assert client.get('/api/search/saved').status_code==401
        assert client.get('/api/search/records?q=a',headers=alice).status_code==422
        assert client.get('/api/search/records?q=travel&category=unknown',headers=alice).status_code==422
        for auth,results in ((alice,{'Alice travel claim'}),(bob,{'Bob travel claim'}),
                             (manager,set()),(admin,{'Alice travel claim','Bob travel claim'})):
            r=client.get('/api/search/records?q=travel&category=expenses',headers=auth)
            assert r.status_code==200,r.text
            assert {item['title'] for item in r.json()['items']}==results,r.text
            assert 'amount' not in r.text and '90' not in r.text
        assert client.get('/api/search/records?q=Candidate&category=recruitment',headers=alice).json()['items']==[]
        assert len(client.get('/api/search/records?q=Candidate&category=recruitment',headers=manager).json()['items'])==1
        assert len(client.get('/api/search/records?q=Candidate&category=recruitment',headers=admin).json()['items'])==1
        assert {i['title'] for i in client.get('/api/search/records?q=Name&category=people',headers=manager).json()['items']} == {'Manager Name','Alice Name','Cora Name'}
        assert {i['title'] for i in client.get('/api/search/records?q=Name&category=people',headers=alice).json()['items']} == {'Alice Name'}
        assert {i['title'] for i in client.get('/api/search/records?q=Special&category=leave',headers=manager).json()['items']} == {'Special Leave'}
        assert {i['title'] for i in client.get('/api/search/records?q=payroll&category=helpdesk',headers=manager).json()['items']} == set()
        assert 'medical confidential' not in client.get('/api/search/records?q=Special&category=leave',headers=admin).text
        assert client.get('/api/search/records?q=secret&category=leave',headers=admin).json()['items']==[]
        assert client.get('/api/search/records',params={'q':'%25','category':'policies'},headers=alice).json()['items'] == []  # literal percent sequence, not wildcard
        r=client.get('/api/search/records',params={'q':'100%','category':'policies'},headers=alice)
        assert r.status_code==200 and [x['title'] for x in r.json()['items']]==['SQL 100% manual'],r.text
        assert client.get('/api/search/records',params={'q':'abc_','category':'policies'},headers=alice).json()['items']==[]
        assert client.post('/api/search/saved',headers=alice,json={'query':' ','category':'all'}).status_code==422
        created=client.post('/api/search/saved',headers=alice,json={'query':'  payroll ','category':'helpdesk'})
        assert created.status_code==201,created.text
        search_id=created.json()['id']
        assert created.json()['query']=='payroll'
        assert client.post('/api/search/saved',headers=alice,json={'query':'payroll','category':'helpdesk'}).status_code==409
        assert client.get('/api/search/saved',headers=bob).json()==[]
        assert client.delete(f'/api/search/saved/{search_id}',headers=bob).status_code==404
        for i in range(1,8):
            assert client.post('/api/search/saved',headers=alice,json={'query':f'keyword{i}','category':'all'}).status_code==201
        assert client.post('/api/search/saved',headers=alice,json={'query':'keyword8','category':'all'}).status_code==422
        assert len(client.get('/api/search/saved',headers=alice).json())==8
        assert client.delete(f'/api/search/saved/{search_id}',headers=alice).status_code==200
        assert len(client.get('/api/search/saved',headers=alice).json())==7
        # All saved searches remain available across future SQL sessions.
        with main.db() as conn:
            assert conn.execute('SELECT COUNT(*) AS n FROM employee_saved_searches WHERE employee_id=?',(ids['Alice'],)).fetchone()['n']==7
        r=client.get('/api/search/records',params={'q':'Alice','offset':0,'limit':1},headers=alice)
        assert r.status_code==200 and len(r.json()['items'])<=1
    print('PASS: v3.7 global search tenant/user isolation, team scope, confidential-field exclusion, wildcard escaping, saved searches and durable storage')

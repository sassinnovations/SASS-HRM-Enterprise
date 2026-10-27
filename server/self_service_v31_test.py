"""v3.1 self-service: isolated request ownership, filters, CSV safety and shortcuts."""
import os
import tempfile
from pathlib import Path
os.environ.update(SASS_HRM_TESTING='1',DB_ENGINE='sqlite',JWT_SECRET='isolated-v31-self-service-secret-longer-than-forty-characters')
with tempfile.TemporaryDirectory(prefix='sass-requests-test-') as d:
    os.environ['DATABASE_PATH']=str(Path(d)/'test.db')
    from fastapi.testclient import TestClient
    import main
    from main import db,hash_password
    with TestClient(main.app) as client:
        with db() as c:
            for code in ('ADM','EMP1','EMP2'):
                role='admin' if code=='ADM' else 'employee'
                c.execute('''INSERT INTO employees(code,name,email,role,designation,department,location,work_mode,join_date,password_hash,account_active)
                  VALUES(?,?,?,?,?,?,?,?,?,?,1)''',(code,code,f'{code.lower()}@example.org',role,'Staff','IT','Hyderabad','Hybrid','2026-01-01',hash_password('PasswordExample12345!')))
            one=c.execute("SELECT id FROM employees WHERE code='EMP1'").fetchone()['id']
            two=c.execute("SELECT id FROM employees WHERE code='EMP2'").fetchone()['id']
            for employee,title in [(one,'My leave'),(two,'Other employee confidential leave')]:
                c.execute("INSERT INTO leave_requests(employee_id,start_date,end_date,leave_type,reason,days,status,created_at) VALUES(?,?,?,?,?,?,?,?)",(employee,'2026-10-20','2026-10-21',title,'Private reasons are not exposed',2,'Pending','2026-10-18T10:00:00+00:00'))
            c.execute('INSERT INTO expenses(employee_id,title,amount,category,status,created_at) VALUES(?,?,?,?,?,?)',
                      (one,'=FORMULA_test',42.0,'Travel','Approved','2026-10-19T10:00:00+00:00'))
            c.execute('INSERT INTO hr_tasks(title,assignee_id,created_by,due_date,priority,created_at) VALUES(?,?,?,?,?,?)',
                      ('Review handbook',one,one,'2026-11-01','Normal','2026-10-16T10:00:00+00:00'))
        def login(code):
            r=client.post('/api/auth/login',json={'email':f'{code.lower()}@example.org','password':'PasswordExample12345!'})
            assert r.status_code==200,r.text
            return {'Authorization':'Bearer '+r.json()['token']}
        first=login('EMP1');second=login('EMP2');admin=login('ADM')
        assert client.get('/api/self-service/activity').status_code==401
        me=client.get('/api/self-service/activity',headers=first)
        assert me.status_code==200,me.text
        assert me.json()['total']==3,me.json()
        assert 'Other employee' not in str(me.json())
        assert 'Private reasons' not in str(me.json())
        assert '42.0' not in str(me.json())
        assert client.get('/api/self-service/activity',headers=admin).json()['total']==0
        assert client.get('/api/self-service/activity',headers=second).json()['total']==1
        assert client.get('/api/self-service/activity?kind=leave&status=active',headers=first).json()['total']==1
        assert client.get('/api/self-service/activity?status=completed',headers=first).json()['total']==1
        assert client.get('/api/self-service/activity?kind=expenses&search=FORMULA',headers=first).json()['total']==1
        assert client.get('/api/self-service/activity?offset=1&limit=1',headers=first).json()['items'][0]['kind']=='leave'
        assert client.get('/api/self-service/activity?kind=employees',headers=first).status_code==422
        assert client.get('/api/self-service/activity?limit=300',headers=first).status_code==422
        export=client.get('/api/self-service/activity.csv',headers=first)
        assert export.status_code==200 and 'attachment' in export.headers['content-disposition']
        assert "'=FORMULA_test" in export.text
        assert 'Other employee' not in export.text
        assert client.get('/api/self-service/activity.csv').status_code==401
        assert client.get('/api/self-service/shortcuts',headers=first).json()=={'pages':[]}
        assert client.put('/api/self-service/shortcuts',headers=first,json={'pages':['calendar','selfservice']}).json()=={'pages':['calendar','selfservice']}
        assert client.get('/api/self-service/shortcuts',headers=second).json()=={'pages':[]}
        assert client.put('/api/self-service/shortcuts',headers=first,json={'pages':['accounts']}).status_code==422
        assert client.put('/api/self-service/shortcuts',headers=first,json={'pages':['leave','leave']}).status_code==422
        assert client.put('/api/self-service/shortcuts',headers=first,json={'pages':['dashboard']*9}).status_code==422
        assert client.get('/api/self-service/shortcuts',headers=first).json()['pages']==['calendar','selfservice']
        with db() as c:
            assert c.execute("SELECT COUNT(*) AS n FROM audit_events WHERE action='workspace.shortcuts.updated'").fetchone()['n']==1
    print('PASS v3.1: owner-scope, pagination, search, filtering, secure CSV, JWT and persistent shortcuts')

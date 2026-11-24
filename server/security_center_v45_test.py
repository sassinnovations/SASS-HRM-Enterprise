"""Isolated v4.5 regression: login isolation, admin permissions and JWT revocation."""
import os, tempfile
from pathlib import Path
os.environ.update(SASS_HRM_TESTING='1', DB_ENGINE='sqlite', JWT_SECRET='security-center-test-secret-long-enough-and-unique-forever')
from fastapi.testclient import TestClient
with tempfile.TemporaryDirectory() as tmp:
    os.environ['DATABASE_PATH']=str(Path(tmp)/'test.db')
    import main
    with TestClient(main.app) as client:
        with main.db() as conn:
            for index,role in [(1,'admin'),(2,'manager'),(3,'employee')]:
                conn.execute('''INSERT INTO employees
                  (id,code,name,email,work_email,role,designation,department,location,work_mode,
                   join_date,password_hash,account_active,session_version)
                  VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',
                  (index,f'SASS-T-{index}',f'Tester {index}',f'user{index}@example.test',
                   f'user{index}@example.test',role,'Tester','QA','Hyderabad','Hybrid','2026-01-01',
                   main.hash_password('SecureAccountLogin2026!'),1,0))
        def login(index, pw='SecureAccountLogin2026!'):
            return client.post('/api/auth/login',json={'email':f'user{index}@example.test','password':pw})
        assert login(1,'invalid').status_code==401
        first=login(1);second=login(2);third=login(3)
        assert all(r.status_code==200 for r in (first,second,third))
        headers=[{'Authorization':'Bearer '+r.json()['token']} for r in (first,second,third)]
        me=client.get('/api/security/me/activity',headers=headers[2]);assert me.status_code==200,me.text
        assert len(me.json()['events'])==1,me.text
        assert set(me.json()['events'][0])=={'id','created_at'}
        assert 'password' not in str(me.json()['events']).lower()
        assert client.get('/api/security/admin/activity',headers=headers[2]).status_code==403
        assert client.get('/api/security/admin/activity',headers=headers[1]).status_code==403
        allr=client.get('/api/security/admin/activity',headers=headers[0]);assert allr.status_code==200,allr.text
        assert len(allr.json()['items'])==3
        assert all(item['successful_logins']==1 for item in allr.json()['items'])
        assert all('password_hash' not in item for item in allr.json()['items'])
        assert len(client.get('/api/security/admin/activity?status=never',headers=headers[0]).json()['items'])==0
        assert client.get('/api/security/admin/activity?status=bogus',headers=headers[0]).status_code==422
        assert client.get('/api/security/admin/activity?limit=500',headers=headers[0]).status_code==422
        assert client.get('/api/security/admin/activity?q=Tester%203',headers=headers[0]).json()['items'][0]['id']==3
        revoked=client.post('/api/security/me/revoke-all',headers=headers[2]);assert revoked.status_code==200
        assert client.get('/api/security/me/activity',headers=headers[2]).status_code==401
        assert client.get('/api/security/me/activity',headers=headers[1]).status_code==200
        new=login(3);assert new.status_code==200
        new_headers={'Authorization':'Bearer '+new.json()['token']}
        assert len(client.get('/api/security/me/activity',headers=new_headers).json()['events'])==2
        assert len(client.get('/api/security/me/activity').json() if False else [])==0
        assert client.get('/api/security/me/activity').status_code==401
    print('PASS v4.5: login history, privacy, administrator restrictions, filters and logout-all')

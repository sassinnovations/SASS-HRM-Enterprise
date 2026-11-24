"""Isolated calendar CRUD, validation, privacy and audit regression."""
import os, sys, tempfile
from pathlib import Path
from unittest.mock import patch
os.environ.update(SASS_HRM_TESTING='1',DB_ENGINE='sqlite',JWT_SECRET='calendar-unit-test-secret-value-over-forty-chars-not-for-production')
with tempfile.TemporaryDirectory() as temp:
    os.environ['DATABASE_PATH']=str(Path(temp)/'calendar-test.sqlite')
    from fastapi.testclient import TestClient
    import main, create_admin
    with TestClient(main.app) as c:
        with patch.object(sys,'argv',['create_admin.py','--email','hr@example.org','--name','Test Admin','--code','ADMIN-1','--location','HQ']),patch.object(create_admin.getpass,'getpass',side_effect=['AdminCalendarUnitTest2026!']*2):
            create_admin.main()
        login=c.post('/api/auth/login',json={'email':'hr@example.org','password':'AdminCalendarUnitTest2026!'})
        assert login.status_code==200, login.text
        admin={'Authorization':'Bearer '+login.json()['token']}
        for i in [1,2]:
            with main.db() as db:
                db.execute('''INSERT INTO employees(code,name,email,role,designation,department,location,work_mode,join_date,password_hash,account_active)
                  VALUES(?,?,?,?,?,?,?,?,?,?,1)''',(f'EMP-{i}',f'Employee {i}',f'emp{i}@example.org','employee','Engineer','Engineering','HQ','On-site','2026-10-10',main.hash_password('EmployeeCalendarTest2026!')))
        def auth(email):
            response=c.post('/api/auth/login',json={'email':email,'password':'EmployeeCalendarTest2026!'})
            assert response.status_code==200,response.text
            return {'Authorization':'Bearer '+response.json()['token']}
        alice,bob=auth('emp1@example.org'),auth('emp2@example.org')
        url='/api/calendar/personal'
        event={'day':'2026-11-23','start_time':'09:45','title':'Prepare for review','notes':'Private notes'}
        assert c.get(url).status_code==401
        assert c.post(url,json=event).status_code==401
        assert c.post(url,headers=alice,json={**event,'start_time':'25:90'}).status_code==422
        assert c.post(url,headers=alice,json={**event,'title':' '}).status_code==422
        response=c.post(url,headers=alice,json=event)
        assert response.status_code==201,response.text
        idx=response.json()['id']
        assert len(c.get(url,headers=alice).json())==1
        assert c.get(url,headers=bob).json()==[]
        assert c.patch(f'{url}/{idx}',headers=bob,json=event).status_code==404
        assert c.delete(f'{url}/{idx}',headers=bob).status_code==404
        assert c.get(url,headers=admin).json()==[]
        assert c.patch(f'{url}/{idx}',headers=alice,json={**event,'title':'Updated meeting'}).status_code==200
        assert c.get(url,headers=alice).json()[0]['title']=='Updated meeting'
        assert c.delete(f'{url}/{idx}',headers=alice).status_code==200
        assert c.get(url,headers=alice).json()==[]
        with main.db() as db:
            audit=[r[0] for r in db.execute("SELECT action FROM audit_events WHERE action LIKE 'calendar.personal.%'")]
        assert audit==['calendar.personal.created','calendar.personal.updated','calendar.personal.deleted'],audit
        print('PASS v2.7 calendar: create/edit/delete, malformed time, unauthorized access, cross-user 404, audit')

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
        settings_url='/api/calendar/preferences'
        defaults={'week_start':'monday','visibility':'all','default_start_time':'','include_private_export':False,'preferred_view':'month','agenda_days':14}
        settings={'week_start':'sunday','visibility':'personal','default_start_time':'08:30','include_private_export':True,'preferred_view':'agenda','agenda_days':7}
        assert c.get(settings_url).status_code==401
        assert c.put(settings_url,json=settings).status_code==401
        assert c.get(settings_url,headers=alice).json()==defaults
        assert c.put(settings_url,headers=alice,json={**settings,'default_start_time':'09:90'}).status_code==422
        assert c.put(settings_url,headers=alice,json={**settings,'week_start':'friday'}).status_code==422
        assert c.put(settings_url,headers=alice,json={**settings,'employee_id':3}).status_code==422
        assert c.put(settings_url,headers=alice,json={**settings,'preferred_view':'custom'}).status_code==422
        assert c.put(settings_url,headers=alice,json={**settings,'agenda_days':31}).status_code==422
        for payload in [settings,defaults,settings]:
            saved=c.put(settings_url,headers=alice,json=payload)
            assert saved.status_code==200,saved.text
            assert c.get(settings_url,headers=alice).json()==payload
        legacy = {key: value for key, value in settings.items() if key not in ('preferred_view', 'agenda_days')}
        assert c.put(settings_url,headers=alice,json=legacy).json()==settings
        assert c.get(settings_url,headers=alice).json()==settings
        assert c.get(settings_url,headers=bob).json()==defaults
        assert c.get(settings_url,headers=admin).json()==defaults
        event={'day':'2026-11-23','start_time':'09:45','title':'Prepare for review','notes':'Private notes'}
        assert c.get(url).status_code==401
        assert c.post(url,json=event).status_code==401
        assert c.post(url,headers=alice,json={**event,'start_time':'25:90'}).status_code==422
        assert c.post(url,headers=alice,json={**event,'title':' '}).status_code==422
        response=c.post(url,headers=alice,json=event)
        assert response.status_code==201,response.text
        idx=response.json()['id']
        cat_url='/api/calendar/categories'
        assert c.get(cat_url).status_code==401
        assert c.post(cat_url,json={'name':'Private'}).status_code==401
        assert c.post(cat_url,headers=alice,json={'name':'Private','color':'red'}).status_code==422
        first=c.post(cat_url,headers=alice,json={'name':' Health   errands ', 'color':'rose'})
        assert first.status_code==201,first.text
        first_id=first.json()['id']
        assert first.json()['name']=='Health errands'
        assert c.post(cat_url,headers=alice,json={'name':'HEALTH errands'}).status_code==409
        second=c.post(cat_url,headers=bob,json={'name':'HEALTH errands'})
        assert second.status_code==201,second.text
        second_id=second.json()['id']
        assert c.get(cat_url,headers=admin).json()==[]
        assert c.get(cat_url,headers=bob).json()[0]['id']==second_id
        assert c.patch(f'{cat_url}/{first_id}',headers=bob,json={'name':'Unowned'}).status_code==404
        assert c.delete(f'{cat_url}/{first_id}',headers=admin).status_code==404
        rejected=c.patch(f'{url}/{idx}',headers=alice,json={**event,'title':'Rejected edit','category_id':second_id})
        assert rejected.status_code==404,rejected.text
        assert c.get(url,headers=alice).json()[0]['title']==event['title']
        calendar=c.get(url,headers=alice)
        assert calendar.headers.get('Cache-Control')=='no-store'
        assert len(calendar.json())==1
        for params in [dict(start='2026-11-01'),dict(start='2026-11-24',end='2026-11-23'),
                       dict(start='2026-11-01',end='2027-02-01')]:
            assert c.get(url,headers=alice,params=params).status_code==422
        bounds=dict(start='2026-11-23',end='2026-11-23')
        assert c.get(url,headers=alice,params=bounds).json()[0]['id']==idx
        assert c.get(url,headers=bob,params=bounds).json()==[]
        assert c.get(url,headers=alice,params=dict(start='2026-12-01',end='2026-12-31')).json()==[]
        assert c.post(url,headers=alice,json={**event,'employee_id':3}).status_code==422
        assert c.patch(f'{url}/{idx}',headers=admin,json=event).status_code==404
        assert c.delete(f'{url}/{idx}',headers=admin).status_code==404
        assert c.get(url,headers=bob).json()==[]
        assert c.patch(f'{url}/{idx}',headers=bob,json=event).status_code==404
        assert c.delete(f'{url}/{idx}',headers=bob).status_code==404
        assert c.get(url,headers=admin).json()==[]
        assert c.patch(f'{url}/{idx}',headers=alice,json={**event,'title':'Updated meeting'}).status_code==200
        assert c.get(url,headers=alice).json()[0]['title']=='Updated meeting'
        assert c.patch(f'{url}/{idx}',headers=alice,json={**event,'category_id':first_id}).status_code==200
        assigned=c.get(url,headers=alice).json()[0]
        assert assigned['category_id']==first_id and assigned['category_name']=='Health errands' and assigned['category_color']=='rose'
        assert c.get(cat_url,headers=alice).json()[0]['event_count']==1
        assert c.patch(f'{url}/{idx}',headers=alice,json=event).status_code==200  # legacy/AI payload
        assert c.get(url,headers=alice).json()[0]['category_id']==first_id
        assert c.patch(f'{cat_url}/{first_id}',headers=alice,json={'name':'Personal plans','color':'green'}).status_code==200
        assert c.get(url,headers=alice).json()[0]['category_name']=='Personal plans'
        assert c.delete(f'{cat_url}/{first_id}',headers=alice).status_code==200
        reachable=c.get(url,headers=alice).json()
        assert len(reachable)==1 and reachable[0]['id']==idx and reachable[0]['category_id'] is None
        assert c.delete(f'{url}/{idx}',headers=alice).status_code==200
        assert c.get(url,headers=alice).json()==[]
        with main.db() as db:
            settings_audit=db.execute("SELECT count(*) FROM audit_events WHERE action='calendar.preferences.updated'").fetchone()[0]
            assert settings_audit==4
            audit=[r[0] for r in db.execute("SELECT action FROM audit_events WHERE action LIKE 'calendar.personal.%'")]
        assert audit==['calendar.personal.created','calendar.personal.updated','calendar.personal.updated','calendar.personal.updated','calendar.personal.deleted'],audit
        print('PASS personal calendar: CRUD, date ranges, settings and category CRUD, category ownership and persistence, legacy compatibility, administrator isolation, audit')

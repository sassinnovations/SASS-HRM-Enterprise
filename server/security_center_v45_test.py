"""Isolated v4.5 regression: login isolation, admin permissions and JWT revocation."""
import csv, io, os, tempfile
from datetime import datetime, timedelta, timezone
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
        export_url='/api/security/me/activity/export.csv'
        own_timestamp=me.json()['events'][0]['created_at']
        own_day=own_timestamp[:10]
        other_timestamp=client.get('/api/security/me/activity',headers=headers[0]).json()['events'][0]['created_at']
        assert client.get(export_url).status_code==401
        assert client.get(export_url+'?start_date=bogus',headers=headers[2]).status_code==422
        previous_day=(datetime.fromisoformat(own_timestamp)-timedelta(days=1)).date().isoformat()
        assert client.get(export_url+'?start_date='+own_day+'&end_date='+previous_day,headers=headers[2]).status_code==422
        def assert_report(result, expected_timestamps):
            assert result.status_code==200,result.text
            assert result.headers['cache-control']=='private, no-store'
            assert result.headers['content-type'].startswith('text/csv')
            assert result.headers['content-disposition']=='attachment; filename="sass-my-sign-ins.csv"'
            assert list(csv.reader(io.StringIO(result.text)))==[['signed_in_at_utc'], *[[s] for s in expected_timestamps]]
        assert_report(client.get(export_url,headers=headers[2],params={'start_date':own_day,'end_date':own_day}),[own_timestamp])
        assert_report(client.get(export_url,headers=headers[0]),[other_timestamp])
        assert_report(client.get(export_url,headers=headers[2],params={'end_date':previous_day}),[])
        old_stamp=(datetime.now(timezone.utc)-timedelta(days=200)).isoformat()
        with main.db() as conn:
            conn.execute('INSERT INTO account_login_events(employee_id,created_at) VALUES(?,?)',(3,old_stamp))
        try:
            assert_report(client.get(export_url,headers=headers[2]),[own_timestamp])
            with main.db() as conn:
                count=conn.execute('SELECT COUNT(*) FROM account_login_events WHERE employee_id=3').fetchone()[0]
                assert count==2, 'Export must not prune official history'
        finally:
            with main.db() as conn:
                conn.execute('DELETE FROM account_login_events WHERE employee_id=? AND created_at=?',(3,old_stamp))
        preferences='/api/security/me/preferences'
        checklist='/api/security/me/checklist'
        settings_url='/api/security/me/checklist-settings'
        for url in (preferences,checklist,settings_url):
            assert client.get(url).status_code==401
        default={'history_limit':30,'display_timezone':'local'}
        configured={'history_limit':10,'display_timezone':'utc'}
        assert client.get(preferences,headers=headers[2]).json()==default
        assert client.put(preferences,headers=headers[2],json=configured).json()==configured
        assert client.get(preferences,headers=headers[2]).json()==configured
        for other in headers[:2]:
            assert client.get(preferences,headers=other).json()==default
        assert client.put(preferences,headers=headers[2],json={'history_limit':200}).status_code==422
        assert client.put(preferences,headers=headers[2],json={'employee_id':2}).status_code==422

        checklist_defaults={'status_filter':'all','sort_order':'due','default_due':'none'}
        checklist_configured={'status_filter':'due','sort_order':'title','default_due':'week'}
        assert client.get(settings_url,headers=headers[2]).json()==checklist_defaults
        assert client.put(settings_url,headers=headers[2],json=checklist_configured).json()==checklist_configured
        assert client.get(settings_url,headers=headers[2]).json()==checklist_configured
        for other in headers[:2]:
            assert client.get(settings_url,headers=other).json()==checklist_defaults
        for invalid in ({'employee_id':2},{'sort_order':'DROP TABLE'},{'status_filter':'bogus'},{'default_due':'yesterday'}):
            assert client.put(settings_url,headers=headers[2],json=invalid).status_code==422
        assert client.get(preferences,headers=headers[2]).json()==configured

        original={'title':' Review sign-ins ', 'due_on':'2026-12-02', 'completed':False}
        result=client.post(checklist,headers=headers[2],json=original)
        assert result.status_code==201,result.text
        item=result.json()
        assert item['title']=='Review sign-ins' and item['due_on']=='2026-12-02' and item['completed'] is False
        item_url=f'{checklist}/{item["id"]}'
        assert client.get(checklist,headers=headers[2]).json()['items']==[item]
        for other in headers[:2]:
            assert client.get(checklist,headers=other).json()['items']==[]
            assert client.put(item_url,headers=other,json=original).status_code==404
            assert client.delete(item_url,headers=other).status_code==404
            assert client.patch(f'{item_url}/completion',headers=other,json={'completed':True}).status_code==404
        completion=f'{item_url}/completion'
        assert client.patch(completion,json={'completed':True}).status_code==401
        assert client.patch(completion,headers=headers[2],json={'completed':True,'title':'Unauthorized payload'}).status_code==422
        assert client.patch(completion,headers=headers[2],json={'completed':'true'}).status_code==422
        updated=client.patch(completion,headers=headers[2],json={'completed':True}).json()
        assert updated['completed'] is True and updated['title']==item['title'] and updated['due_on']==item['due_on']
        assert client.patch(completion,headers=headers[2],json={'completed':False}).json()['completed'] is False
        assert client.post(checklist,headers=headers[2],json={'title':'   '}).status_code==422
        assert client.post(checklist,headers=headers[2],json={'title':'Invalid date','due_on':'2026-02-31'}).status_code==422
        assert client.post(checklist,headers=headers[2],json={'title':'Wrong owner','employee_id':2}).status_code==422
        edited={'title':'Review sign-ins and devices','due_on':None,'completed':True}
        result=client.put(item_url,headers=headers[2],json=edited)
        assert result.status_code==200,result.text
        assert {k:result.json()[k] for k in edited}==edited
        assert client.delete(item_url,headers=headers[2]).status_code==200
        assert client.delete(item_url,headers=headers[2]).status_code==404
        assert client.get(checklist,headers=headers[2]).json()['items']==[]
        assert client.get('/api/security/me/activity',headers=headers[2]).json()['events']==me.json()['events']
        revoked=client.post('/api/security/me/revoke-all',headers=headers[2]);assert revoked.status_code==200
        assert client.get('/api/security/me/activity',headers=headers[2]).status_code==401
        assert client.get('/api/security/me/activity',headers=headers[1]).status_code==200
        new=login(3);assert new.status_code==200
        new_headers={'Authorization':'Bearer '+new.json()['token']}
        assert len(client.get('/api/security/me/activity',headers=new_headers).json()['events'])==2
        assert client.get('/api/security/me/activity').status_code==401
        change='/api/auth/change-password'
        assert client.post(change,headers=new_headers,json={'current_password':'WrongPassword2026!', 'new_password':'AnotherPassword2026!'}).status_code==403
        assert client.post(change,headers=new_headers,json={'current_password':'SecureAccountLogin2026!', 'new_password':'AnotherPassword2026!'}).status_code==200
        assert client.get(preferences,headers=new_headers).status_code==401
        assert login(3,'AnotherPassword2026!').status_code==200
    print('PASS: security history and sessions, private preferences and checklist CRUD, sign-in CSV privacy and dates, and password rotation')

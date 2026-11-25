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
        # Preferences are private; clearing them never touches shortcuts.
        defaults={'default_kind':'all','default_status':'all','page_size':20}
        custom={'default_kind':'leave','default_status':'active','page_size':10}
        assert client.get('/api/self-service/settings').status_code==401
        assert client.get('/api/self-service/settings',headers=first).json()==defaults
        assert client.put('/api/self-service/settings',headers=first,json=custom).json()==custom
        assert client.get('/api/self-service/settings',headers=first).json()==custom
        assert client.get('/api/self-service/settings',headers=admin).json()==defaults
        assert client.put('/api/self-service/settings',headers=first,json={**custom,'page_size':40}).status_code==422
        assert client.put('/api/self-service/settings',headers=first,json={**custom,'default_kind':'admin'}).status_code==422
        assert client.delete('/api/self-service/settings',headers=first).json()==defaults
        assert client.get('/api/self-service/settings',headers=first).json()==defaults

        # Draft display defaults persist per owner and are independent of history.
        draft_view_path='/api/self-service/draft-view'
        default_view={'module_filter':'all','draft_view':'all','sort_order':'newest'}
        custom_view={'module_filter':'leave','draft_view':'pinned','sort_order':'title'}
        assert client.get(draft_view_path).status_code==401
        assert client.get(draft_view_path,headers=first).json()==default_view
        assert client.put(draft_view_path,headers=first,json=custom_view).json()==custom_view
        assert client.get(draft_view_path,headers=first).json()==custom_view
        assert client.get(draft_view_path,headers=second).json()==default_view
        assert client.get(draft_view_path,headers=admin).json()==default_view
        for invalid in ({'sort_order':'invalid'},{'draft_view':'submitted'},{'module_filter':'tasks'},{'query':'private'}):
            assert client.put(draft_view_path,headers=first,json=invalid).status_code==422
        assert client.get(draft_view_path,headers=first).json()==custom_view
        assert client.get('/api/self-service/settings',headers=first).json()==defaults
        assert client.delete(draft_view_path,headers=first).json()==default_view
        assert client.get(draft_view_path,headers=first).json()==default_view

        # Shortcut remove and reorder share the existing, ordered save API.
        assert client.put('/api/self-service/shortcuts',headers=first,
                          json={'pages':['selfservice','calendar','leave']}).json()['pages']==['selfservice','calendar','leave']
        assert client.put('/api/self-service/shortcuts',headers=first,
                          json={'pages':['calendar','leave']}).json()['pages']==['calendar','leave']
        assert client.get('/api/self-service/shortcuts',headers=first).json()['pages']==['calendar','leave']
        assert client.get('/api/self-service/shortcuts',headers=second).json()['pages']==[]

        # Drafts support manual CRUD but cannot change ownership or a real request.
        path='/api/self-service/drafts'
        payload={'kind':'leave','title':' Draft for an October request ','notes':'  Draft-only note  '}
        assert client.post(path,json=payload).status_code==401
        assert client.post(path,headers=first,json={**payload,'employee_id':two}).status_code==422
        assert client.post(path,headers=first,json={**payload,'title':'   '}).status_code==422
        assert client.post(path,headers=first,json={**payload,'kind':'offboarding'}).status_code==422
        created=client.post(path,headers=first,json=payload)
        assert created.status_code==201,created.text
        item=created.json(); draft=f'{path}/{item["id"]}'
        assert item['title']=='Draft for an October request'
        assert item['notes']=='Draft-only note'
        assert item['stage']=='drafting' and item['pinned'] is False
        assert client.get(path,headers=first).json()['items']==[item]
        assert client.get(path,headers=second).json()['items']==[]
        assert client.get(path,headers=admin).json()['items']==[]
        assert client.patch(draft,headers=second,json=payload).status_code==404
        assert client.delete(draft,headers=admin).status_code==404
        edited=client.patch(draft,headers=first,json={**payload,'kind':'helpdesk','title':'Revised helpdesk draft'})
        assert edited.status_code==200 and edited.json()['title']=='Revised helpdesk draft',edited.text
        assert edited.json()['created_at']==item['created_at']
        assert edited.json()['kind']=='helpdesk'
        # Both metadata flags survive partial changes and remain scoped to the draft owner.
        organization=f'{draft}/organization'
        assert client.patch(organization,json={'pinned':True}).status_code==401
        assert client.patch(organization,headers=second,json={'pinned':True}).status_code==404
        assert client.patch(organization,headers=admin,json={'stage':'ready'}).status_code==404
        for invalid in ({},{'stage':None},{'stage':'submitted'},{'pinned':'yes'},{'employee_id':two,'pinned':True}):
            assert client.patch(organization,headers=first,json=invalid).status_code==422
        newer=client.post(path,headers=first,json={**payload,'title':'A newer draft'}).json()
        assert client.get(path,headers=first).json()['items'][0]['id']==newer['id']
        baseline=edited.json()
        pinned=client.patch(organization,headers=first,json={'pinned':True}).json()
        assert pinned['pinned'] is True and pinned['stage']=='drafting'
        ready=client.patch(organization,headers=first,json={'stage':'ready'}).json()
        assert ready['pinned'] is True and ready['stage']=='ready'
        assert ready['title']==baseline['title'] and ready['updated_at']==baseline['updated_at']
        assert [r['id'] for r in client.get(path,headers=first).json()['items']]==[item['id'],newer['id']]
        assert client.get(path,headers=second).json()['items']==[]
        assert client.get(path,headers=admin).json()['items']==[]
        reset=client.patch(organization,headers=first,json={'stage':'drafting','pinned':False}).json()
        assert reset['pinned'] is False and reset['stage']=='drafting'
        with db() as c:
            assert c.execute('SELECT COUNT(*) FROM self_service_draft_organization').fetchone()[0]==0
        assert client.patch(organization,headers=first,json={'stage':'ready','pinned':True}).status_code==200
        edited=client.patch(draft,headers=first,json={**payload,'title':'Content edit preserves organization'}).json()
        assert edited['pinned'] is True and edited['stage']=='ready'
        duplicate=f'{draft}/duplicate'
        assert client.post(duplicate).status_code==401
        assert client.post(duplicate,headers=second).status_code==404
        assert client.post(duplicate,headers=admin).status_code==404
        result=client.post(duplicate,headers=first)
        assert result.status_code==201,result.text
        copy=result.json()
        assert copy['id']!=item['id'] and copy['title']=='Content edit preserves organization (copy)'
        assert copy['kind']==edited['kind'] and copy['notes']==edited['notes']
        assert copy['stage']=='drafting' and copy['pinned'] is False
        assert client.patch(f'{path}/{copy["id"]}',headers=first,json={**payload,'title':'Independent copy edit'}).status_code==200
        assert any(row['id']==item['id'] and row['title']==edited['title'] and row['pinned'] for row in client.get(path,headers=first).json()['items'])
        assert client.delete(f'{path}/{copy["id"]}',headers=first).status_code==200
        with db() as c:
            c.executemany("""INSERT INTO self_service_drafts(employee_id,kind,title,notes,created_at,updated_at)
                             VALUES(?,?,?,?,?,?)""",[(one,'leave','Existing spare draft','','2026-01-01','2026-01-01')]*98)
        assert client.post(duplicate,headers=first).status_code==409
        assert client.post(path,headers=first,json=payload).status_code==409
        with db() as c:
            c.execute("DELETE FROM self_service_drafts WHERE employee_id=? AND title='Existing spare draft'",(one,))
        assert 'Draft-only note' not in client.get('/api/self-service/activity.csv',headers=first).text
        assert client.delete(draft,headers=first).status_code==200
        assert client.delete(draft,headers=first).status_code==404
        assert client.patch(organization,headers=first,json={'pinned':True}).status_code==404
        assert client.delete(f'{path}/{newer["id"]}',headers=first).status_code==200
        with db() as c:
            assert c.execute('SELECT COUNT(*) FROM self_service_draft_organization').fetchone()[0]==0
        assert client.get(path,headers=first).json()['items']==[]
        assert client.get('/api/self-service/activity',headers=first).json()==me.json()
        with db() as c:
            history=c.execute("SELECT action, details FROM audit_events WHERE action LIKE 'workspace.request_draft.%' ORDER BY id").fetchall()
            action_names=[row['action'].rsplit('.',1)[-1] for row in history]
            assert action_names==['created','updated','created','organized','organized','organized','organized','updated','duplicated','updated','deleted','deleted','deleted']
            assert all(row['details']=='' for row in history)
    print('PASS v3.1: owner-scope, pagination, search, filtering, secure CSV, JWT and persistent shortcuts, private draft CRUD, independent history settings, and owner-only stage/pin metadata, independent copies and saved draft views')

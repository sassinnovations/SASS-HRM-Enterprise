"""Isolated v3.0 workflow/inbox regression test: no live MySQL data touched."""
import os
import tempfile
from pathlib import Path

os.environ['SASS_HRM_TESTING']='1'
os.environ['DB_ENGINE']='sqlite'
os.environ['JWT_SECRET']='ISOLATED-TEST-WORKSPACE-V3-SECRET-LONGER-THAN-40-CHARS'

from fastapi.testclient import TestClient
with tempfile.TemporaryDirectory() as tmp:
    os.environ['DATABASE_PATH']=str(Path(tmp)/'workspace-v30.db')
    import main
    from main import db,hash_password
    with TestClient(main.app) as client:
        with db() as c:
            for code,name,email,role in [('ADM','Admin','admin@example.org','admin'),('EMP1','One','one@example.org','employee'),('EMP2','Two','two@example.org','employee')]:
                c.execute('''INSERT INTO employees(code,name,email,role,designation,department,location,work_mode,join_date,manager_id,password_hash,account_active)
                  VALUES(?,?,?,?,?,?,?,?,?,?,?,1)''',(code,name,email,role,'Engineer','IT','Hyderabad','Hybrid','2026-09-01',None,hash_password('PasswordExample12345!')))
            one=c.execute("SELECT id FROM employees WHERE email='one@example.org'").fetchone()['id']
            two=c.execute("SELECT id FROM employees WHERE email='two@example.org'").fetchone()['id']
            c.execute('INSERT INTO notifications(employee_id,title,body,created_at) VALUES(?,?,?,?)',(one,'Employee notice','Task changed','2026-10-19T10:00:00+00:00'))
            c.execute('INSERT INTO notifications(employee_id,title,body,created_at) VALUES(?,?,?,?)',(one,'Pay notice','Payroll available','2026-10-19T10:00:00+00:00'))
            c.execute('INSERT INTO notifications(employee_id,title,body,created_at) VALUES(?,?,?,?)',(two,'Private alert','No access for other staff','2026-10-19T10:00:00+00:00'))
            notification_one=c.execute('SELECT id FROM notifications WHERE employee_id=? ORDER BY id',(one,)).fetchone()['id']
            other_notice=c.execute('SELECT id FROM notifications WHERE employee_id=?',(two,)).fetchone()['id']
        def login(email):
            reply=client.post('/api/auth/login',json={'email':email,'password':'PasswordExample12345!'})
            assert reply.status_code==200,reply.text
            return {'Authorization':'Bearer '+reply.json()['token']}
        admin=login('admin@example.org');first=login('one@example.org');second=login('two@example.org')
        def get(path,auth): return client.get('/api'+path,headers=auth)
        def put(path,auth,payload): return client.put('/api'+path,headers=auth,json=payload)
        def post(path,auth): return client.post('/api'+path,headers=auth)
        assert get('/workspace/settings',first).status_code==200
        assert get('/workspace/settings',first).json()['task_warning_days']==2
        settings={'helpdesk_target_days':5,'task_warning_days':1,'onboarding_warning_days':4,'organization_notice':'Company HR support hours: 9–6.'}
        assert put('/workspace/settings',first,settings).status_code==403
        assert put('/workspace/settings',admin,{**settings,'helpdesk_target_days':31}).status_code==422
        changed=put('/workspace/settings',admin,settings)
        assert changed.status_code==200,changed.text
        assert get('/workspace/settings',first).json()['organization_notice']==settings['organization_notice']
        assert get('/workspace/overview',first).json()['scope']=='personal'
        assert get('/workspace/overview',admin).json()['scope']=='organization'
        inbox=get('/workspace/inbox',first)
        assert inbox.status_code==200,inbox.text
        assert len(inbox.json()['items'])==2
        assert inbox.json()['unread_count']==2
        assert get('/workspace/inbox',second).json()['unread_count']==1
        assert get('/workspace/inbox?filter=garbage',first).status_code==422
        assert get('/workspace/inbox?limit=5000',first).status_code==422
        assert post(f'/workspace/inbox/{other_notice}/archive',first).status_code==403
        assert post(f'/workspace/inbox/{other_notice}/restore',first).status_code==403
        assert post(f'/workspace/inbox/{notification_one}/archive',first).status_code==200
        assert get('/workspace/inbox',first).json()['unread_count']==1
        assert len(get('/workspace/inbox?filter=archived',first).json()['items'])==1
        assert post(f'/workspace/inbox/{notification_one}/restore',first).status_code==200
        assert get('/workspace/inbox',first).json()['unread_count']==2
        assert post('/workspace/inbox/read-all',first).json()['updated']==2
        assert get('/workspace/inbox?filter=unread',first).json()['items']==[]
        assert get('/workspace/inbox',second).json()['unread_count']==1
        prefs={'unread_only':True,'compact_view':True}
        assert put('/workspace/inbox/preferences',first,prefs).json()==prefs
        assert get('/workspace/inbox/preferences',second).json()=={'unread_only':False,'compact_view':False}
        with db() as c:
            count=c.execute("SELECT COUNT(*) AS n FROM audit_events WHERE action='workspace.settings.updated'").fetchone()['n']
            assert count==1
    print('PASS v3.0 workspace: account scoping, inbox archive/restore/read, preferences, HR settings, validation, audit, overview')

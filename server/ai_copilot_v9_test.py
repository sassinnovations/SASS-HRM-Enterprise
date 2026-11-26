"""AI v9 isolated catalog-CRUD regression; SQLite only, no production data or provider calls."""
import os, sys, tempfile
from pathlib import Path
from unittest.mock import patch

os.environ.update(SASS_HRM_TESTING='1', DB_ENGINE='sqlite',
                  JWT_SECRET='isolated-long-v9-password-independent-test-secret',
                  AI_COPILOT_GENERATION='0', AI_API_KEY='')
from fastapi.testclient import TestClient

with tempfile.TemporaryDirectory() as tmp:
    os.environ['DATABASE_PATH']=str(Path(tmp)/'v9.sqlite')
    import main, create_admin
    with TestClient(main.app) as client:
        with patch.object(sys,'argv',['create_admin.py','--email','admin@example.test','--name','Admin','--code','ADM9','--location','Hyderabad']), \
             patch.object(create_admin.getpass,'getpass',side_effect=['StrongV9AdminPassword!']*2):
            create_admin.main()
        with main.db() as c:
            c.execute('''INSERT INTO employees(code,name,email,role,designation,department,location,work_mode,join_date,password_hash,account_active)
                         VALUES(?,?,?,?,?,?,?,?,?,?,1)''',
                      ('STAFF9','Staff','staff@example.test','employee','Analyst','Operations','Hyderabad','Hybrid','2026-01-01',main.hash_password('StrongV9StaffPassword!')))
        def auth(email,password):
            resp=client.post('/api/auth/login',json={'email':email,'password':password})
            assert resp.status_code==200,resp.text
            return {'Authorization':'Bearer '+resp.json()['token']}
        admin=auth('admin@example.test','StrongV9AdminPassword!')
        staff=auth('staff@example.test','StrongV9StaffPassword!')
        actions=client.get('/api/ai/copilot/actions/catalog',headers=admin).json()
        assert len(actions)==31, (len(actions), actions)
        assert len(client.get('/api/ai/copilot/actions/catalog',headers=staff).json())==14 or not any(x['operation'].startswith('admin_') for x in client.get('/api/ai/copilot/actions/catalog',headers=staff).json())
        for op in ('admin_office_create','admin_category_create','admin_template_create','admin_office_delete'):
            assert not any(x['operation']==op for x in client.get('/api/ai/copilot/actions/catalog',headers=staff).json())
            assert client.post('/api/ai/copilot/actions/prepare',headers=staff,json={'operation':op,'parameters':{}}).status_code==403

        def prepare(operation, params):
            resp=client.post('/api/ai/copilot/actions/prepare',headers=admin,json={'operation':operation,'parameters':params})
            assert resp.status_code==201,(operation,resp.status_code,resp.text)
            return resp.json()['proposal_id']
        def confirm(pid):
            resp=client.post(f'/api/ai/copilot/actions/{pid}/confirm',headers=admin,json={'confirm':'CONFIRM'})
            assert resp.status_code==200,(resp.status_code,resp.text)
            assert resp.json()['state']=='Executed'
            assert client.post(f'/api/ai/copilot/actions/{pid}/confirm',headers=admin,json={'confirm':'CONFIRM'}).status_code==409
            return resp.json()['result']
        office={'code':'HYD9','name':'V9 Test Office','city':'Hyderabad','country':'India','timezone':'Asia/Kolkata','address':'Test only','is_active':True}
        pid=prepare('admin_office_create',office)
        with main.db() as c: assert c.execute("SELECT COUNT(*) FROM organization_offices WHERE code='HYD9'").fetchone()[0]==0
        confirm(pid)
        with main.db() as c: office_id=c.execute("SELECT id FROM organization_offices WHERE code='HYD9'").fetchone()['id']
        opts=client.get('/api/ai/copilot/actions/my-options',headers=admin).json()
        assert any(x['id']==office_id for x in opts['offices'])
        assert client.get('/api/ai/copilot/actions/my-options',headers=staff).json()['offices']==[]
        old=prepare('admin_office_edit',{'office_id':office_id,**{**office,'city':'Secunderabad'}})
        # A concurrent admin edit invalidates the prepared confirmation.
        with main.db() as c: c.execute('UPDATE organization_offices SET city=? WHERE id=?',('Somewhere Else',office_id))
        stale=client.post(f'/api/ai/copilot/actions/{old}/confirm',headers=admin,json={'confirm':'CONFIRM'})
        assert stale.status_code==409,stale.text
        confirm(prepare('admin_office_edit',{'office_id':office_id,**office,'city':'Secunderabad'}))
        confirm(prepare('admin_office_deactivate',{'office_id':office_id}))
        confirm(prepare('admin_office_activate',{'office_id':office_id}))
        # Existing employee location references block destructive office mutations.
        with main.db() as c:
            c.execute("UPDATE employees SET location='V9 Test Office' WHERE code='STAFF9'")
        linked=prepare('admin_office_delete',{'office_id':office_id,'reason':'Linked office should stay'})
        denied=client.post(f'/api/ai/copilot/actions/{linked}/confirm',headers=admin,json={'confirm':'CONFIRM'})
        assert denied.status_code==409,denied.text
        with main.db() as c:
            c.execute("UPDATE employees SET location='Hyderabad' WHERE code='STAFF9'")
        assert client.post('/api/ai/copilot/actions/prepare',headers=admin,json={'operation':'admin_office_delete','parameters':{'office_id':office_id,'reason':'no'}}).status_code==422
        confirm(prepare('admin_office_delete',{'office_id':office_id,'reason':'Duplicate test office'}))

        category={'name':'V9 Test Service','description':'Admin-only category'}
        cid=confirm(prepare('admin_category_create',category))['id']
        confirm(prepare('admin_category_edit',{'category_id':cid,'name':'V9 Renamed Service','description':'Changed'}))
        confirm(prepare('admin_category_archive',{'category_id':cid}))
        confirm(prepare('admin_category_restore',{'category_id':cid}))
        not_archived=prepare('admin_category_delete',{'category_id':cid,'reason':'Test cleanup'})
        denied=client.post(f'/api/ai/copilot/actions/{not_archived}/confirm',headers=admin,json={'confirm':'CONFIRM'})
        assert denied.status_code==409,denied.text
        confirm(prepare('admin_category_archive',{'category_id':cid}))
        # Historical service requests must prevent catalog deletion.
        with main.db() as c:
            staff_id=c.execute("SELECT id FROM employees WHERE code='STAFF9'").fetchone()[0]
            c.execute('''INSERT INTO service_requests(employee_id,category_id,subject,details,created_at,updated_at)
                         VALUES(?,?,?,?,?,?)''',(staff_id,cid,'Linked request','Preserve this request','2026-11-25','2026-11-25'))
        linked=prepare('admin_category_delete',{'category_id':cid,'reason':'Category has linked request'})
        denied=client.post(f'/api/ai/copilot/actions/{linked}/confirm',headers=admin,json={'confirm':'CONFIRM'})
        assert denied.status_code==409,denied.text
        # The disposable row is removed only in this isolated test database.
        with main.db() as c:
            c.execute('DELETE FROM service_requests WHERE category_id=?',(cid,))
        confirm(prepare('admin_category_delete',{'category_id':cid,'reason':'Unused test category'}))

        template={'title':'V9 Test HR Task','guidance':'Follow the onboarding checklist','priority':'Normal','due_offset_days':7}
        tid=confirm(prepare('admin_template_create',template))['id']
        confirm(prepare('admin_template_edit',{'template_id':tid,**{**template,'title':'V9 Renamed Task','due_offset_days':14}}))
        confirm(prepare('admin_template_archive',{'template_id':tid}))
        confirm(prepare('admin_template_restore',{'template_id':tid}))
        confirm(prepare('admin_template_archive',{'template_id':tid}))
        confirm(prepare('admin_template_delete',{'template_id':tid,'reason':'Unused v9 task template'}))

        hist=client.get('/api/ai/copilot/actions/history',headers=admin)
        assert hist.status_code==200 and hist.json()['items'] and hist.json()['scope']=='my_actions_only'
        assert client.get('/api/ai/copilot/actions/history',headers=staff).json()['items']==[]
        assert client.get('/api/ai/copilot/actions/history').status_code==401
        visible={r['key']:r for r in client.get('/api/ai/copilot/features',headers=admin).json()}
        for key in ('orgsettings','requestdesk','tasktemplates'):
            assert visible[key]['copilot_actions'],key
        assert len(visible)==72
        with main.db() as c:
            assert c.execute("SELECT COUNT(*) FROM ai_action_proposals WHERE state='Executed'").fetchone()[0]>=10
            assert c.execute("SELECT COUNT(*) FROM audit_events WHERE action='ai.action.confirmed'").fetchone()[0]>=10
        print('PASS AI v9: 31 allowlisted actions; office, service catalog and template CRUD; stale guards; role scoping; ownership; audit/history')

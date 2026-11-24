"""Isolated workflow regression: safe management of both shared catalogs."""
import os
import tempfile
from pathlib import Path
from datetime import date, timedelta
os.environ.update(SASS_HRM_TESTING='1',DB_ENGINE='sqlite',JWT_SECRET='catalog-management-isolated-testing-secret-abcdef-123456789')
from fastapi.testclient import TestClient
with tempfile.TemporaryDirectory() as folder:
    os.environ['DATABASE_PATH']=str(Path(folder)/'catalog.sqlite')
    import main
    with TestClient(main.app) as client:
        with main.db() as c:
            for code,role in [('HRADMIN','admin'),('STAFF','employee')]:
                c.execute('''INSERT INTO employees(code,name,email,role,designation,department,location,join_date,password_hash,account_active)
                  VALUES(?,?,?,?,?,?,?,?,?,1)''',(code,code,code.lower()+'@test.invalid',role,'QA','IT','Hyderabad','2026-01-01',main.hash_password('TestCatalogPassword123!')))
            eid=c.execute("SELECT id FROM employees WHERE code='STAFF'").fetchone()[0]
        def token(code):
            r=client.post('/api/auth/login',json={'email':code.lower()+'@test.invalid','password':'TestCatalogPassword123!'})
            assert r.status_code==200,r.text
            return {'Authorization':'Bearer '+r.json()['token']}
        admin,staff=token('HRADMIN'),token('STAFF')
        def req(method,path,header=admin,body=None):
            return client.request(method,'/api'+path,headers=header,json=body)
        cat={'name':'Company ID letter','description':'Verified employment document'}
        assert req('POST','/request-desk/categories',staff,cat).status_code==403
        x=req('POST','/request-desk/categories',admin,cat)
        assert x.status_code==201,x.text
        catid=x.json()['id'];path=f'/request-desk/categories/{catid}'
        assert req('POST','/request-desk/categories',admin,{**cat,'name':'company id letter'}).status_code==409
        assert req('PUT',path,staff,cat).status_code==403
        assert req('PUT',path,admin,{**cat,'name':'New staff letter'}).status_code==200
        assert req('DELETE',path,admin,{'confirm':'DELETE','reason':'Cleanup unused category'}).status_code==409
        assert req('PATCH',path+'/state',staff,{'active':False}).status_code==403
        assert req('PATCH',path+'/state',admin,{'active':False}).status_code==200
        assert req('GET','/request-desk/categories',staff).json()==[]
        assert req('GET','/request-desk/categories?include_archived=true',staff).status_code==403
        assert len(req('GET','/request-desk/categories?include_archived=true',admin).json())==1
        assert req('DELETE',path,admin,{'confirm':'REMOVE','reason':'Cleanup unused category'}).status_code==422
        assert req('DELETE',path,admin,{'confirm':'DELETE','reason':'Cleanup unused category'}).status_code==200
        assert req('GET','/request-desk/categories?include_archived=true',admin).json()==[]
        linked=req('POST','/request-desk/categories',admin,{'name':'Identity document','description':'Service request'})
        assert linked.status_code==201,linked.text
        lid=linked.json()['id']
        sr=req('POST','/request-desk/requests',staff,{'category_id':lid,'subject':'Need ID document','details':'Help with my employment ID record'})
        assert sr.status_code==201,sr.text
        assert req('PATCH',f'/request-desk/categories/{lid}/state',admin,{'active':False}).status_code==200
        assert req('DELETE',f'/request-desk/categories/{lid}',admin,{'confirm':'DELETE','reason':'Try to remove linked records'}).status_code==409
        assert req('GET','/request-desk/requests',staff).json()[0]['category_name']=='Identity document'

        template={'title':'Employee induction letter','guidance':'Verify documents with the staff member',
                  'priority':'Normal','due_offset_days':5}
        assert req('POST','/workforce/task-templates',staff,template).status_code==403
        record=req('POST','/workforce/task-templates',admin,template)
        assert record.status_code==201,record.text
        tid=record.json()['id'];tpath=f'/workforce/task-templates/{tid}'
        assert req('PUT',tpath,staff,template).status_code==403
        assert req('PUT',tpath,admin,{**template,'title':'Updated induction letter','priority':'High','due_offset_days':8}).status_code==200
        assert req('POST','/workforce/task-templates',admin,{**template,'title':'updated INDUCTION letter'}).status_code==409
        assert req('DELETE',tpath,admin,{'confirm':'DELETE','reason':'Unused template cleanup'}).status_code==409
        assert req('PATCH',tpath,admin,{'active':False}).status_code==200
        assert req('DELETE',tpath,staff,{'confirm':'DELETE','reason':'Unused template cleanup'}).status_code==403
        assert req('DELETE',tpath,admin,{'confirm':'DELETE','reason':'Unused template cleanup'}).status_code==200
        record=req('POST','/workforce/task-templates',admin,{**template,'title':'Onboarding requirements'})
        assert record.status_code==201,record.text
        tid=record.json()['id'];tpath=f'/workforce/task-templates/{tid}'
        start=(date.today()+timedelta(days=1)).isoformat()
        response=req('POST',tpath+'/assign',admin,{'employee_id':eid,'start_date':start})
        assert response.status_code==201,response.text
        task_id=response.json()['task_id']
        assert req('PUT',tpath,admin,{**template,'title':'Updated onboarding requirements'}).status_code==200
        with main.db() as c:
            assigned=c.execute('SELECT title FROM hr_tasks WHERE id=?',(task_id,)).fetchone()
            assert assigned['title']=='Onboarding requirements','Template changes must not silently rewrite assigned work'
        assert req('PATCH',tpath,admin,{'active':False}).status_code==200
        assert req('DELETE',tpath,admin,{'confirm':'DELETE','reason':'Cannot remove used template'}).status_code==409
        with main.db() as c:
            assert c.execute('SELECT COUNT(*) FROM hr_task_template_assignments WHERE template_id=?',(tid,)).fetchone()[0]==1
            actions={r['action'] for r in c.execute('SELECT action FROM audit_events').fetchall()}
            for action in ('requestdesk.category.updated','requestdesk.category.state','requestdesk.category.deleted',
                           'task.template.updated','task.template.state','task.template.deleted','task.template.assigned'):
                assert action in actions,action
        print('PASS: service catalog and HR template create/edit/archive/restore/delete guards, permissions, references, task history and audit')

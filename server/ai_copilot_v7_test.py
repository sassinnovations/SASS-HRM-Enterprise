"""Isolated AI v7 tests: employee pending-work summary + controlled bulk knowledge import.
No external LLM or live database. Run: python server/ai_copilot_v7_test.py
"""
from __future__ import annotations
import os, sys, tempfile
from pathlib import Path
from unittest.mock import patch

os.environ.update(SASS_HRM_TESTING='1', DB_ENGINE='sqlite',
                  JWT_SECRET='v7-secret-for-isolated-ai-integration-tests-2026',
                  AI_COPILOT_GENERATION='0', AI_API_KEY='')
from fastapi.testclient import TestClient

with tempfile.TemporaryDirectory() as root:
    os.environ['DATABASE_PATH']=str(Path(root)/'test.sqlite')
    import main, create_admin
    ai=main.ai_copilot
    with TestClient(main.app) as client:
        with patch.object(sys,'argv',['create_admin.py','--email','hr@example.test','--name','HR Admin','--code','ADM-V7','--location','Hyderabad']),\
             patch.object(create_admin.getpass,'getpass',side_effect=['StrongAdminV7Password!']*2):
            create_admin.main()
        with main.db() as c:
            for code,email,role in [('EMP-V7','employee@example.test','employee'),('MGR-V7','manager@example.test','manager')]:
                c.execute('''INSERT INTO employees(code,name,email,role,designation,department,location,work_mode,join_date,password_hash,account_active)
                             VALUES(?,?,?,?,?,?,?,?,?,?,1)''',
                          (code,'Test '+code,email,role,'Analyst','People','Hyderabad','Hybrid','2026-01-04', main.hash_password('StrongEmployeeV7!')))
            staff_id=c.execute("SELECT id FROM employees WHERE code='EMP-V7'").fetchone()[0]
            mgr_id=c.execute("SELECT id FROM employees WHERE code='MGR-V7'").fetchone()[0]
            now=ai.utcnow()
            c.execute('''INSERT INTO leave_requests(employee_id,start_date,end_date,leave_type,reason,days,status,created_at)
                         VALUES(?,?,?,?,?,?,?,?)''',(staff_id,'2026-12-01','2026-12-02','Annual Leave','Personal',2,'Pending',now))
            c.execute('''INSERT INTO leave_requests(employee_id,start_date,end_date,leave_type,reason,days,status,created_at)
                         VALUES(?,?,?,?,?,?,?,?)''',(mgr_id,'2026-12-03','2026-12-04','Annual Leave','Manager',2,'Pending',now))
            c.execute('''INSERT INTO hr_tasks(title,assignee_id,created_by,due_date,priority,status,created_at)
                         VALUES(?,?,?,?,?,?,?)''',('Staff task',staff_id,mgr_id,'2026-12-15','Normal','Open',now))
            c.execute('''INSERT INTO hr_tasks(title,assignee_id,created_by,due_date,priority,status,created_at)
                         VALUES(?,?,?,?,?,?,?)''',('Manager task',mgr_id,mgr_id,'2026-12-15','Normal','Open',now))
            c.execute("INSERT INTO expenses(employee_id,title,amount,currency,category,status,created_at) VALUES(?,?,?,?,?,?,?)",
                      (staff_id,'Taxi',100,'INR','Travel','Pending',now))
            c.execute("INSERT INTO expenses(employee_id,title,amount,currency,category,status,created_at) VALUES(?,?,?,?,?,?,?)",
                      (mgr_id,'Private manager expense',200,'INR','Travel','Pending',now))

        def headers(email,password):
            resp=client.post('/api/auth/login',json={'email':email,'password':password})
            assert resp.status_code==200,resp.text
            return {'Authorization':'Bearer '+resp.json()['token']}
        admin=headers('hr@example.test','StrongAdminV7Password!')
        staff=headers('employee@example.test','StrongEmployeeV7!')
        manager=headers('manager@example.test','StrongEmployeeV7!')
        assert client.get('/api/ai/copilot/my-pending').status_code==401
        snap=client.get('/api/ai/copilot/my-pending',headers=staff)
        assert snap.status_code==200,snap.text
        values={item['key']:item['count'] for item in snap.json()['items']}
        assert snap.json()['total']==3 and values['leave']==values['tasks']==values['expenses']==1,values
        assert snap.json()['scope']=='own_records_only'
        manager_snap=client.get('/api/ai/copilot/my-pending',headers=manager).json()
        assert manager_snap['total']==3,manager_snap
        answer=client.post('/api/ai/copilot/ask',headers=staff,json={'message':'What needs my attention?'}).json()
        assert answer['mode']=='data-backed' and answer['snapshot']['total']==3,answer
        assert 'Private manager expense' not in str(answer)
        assert not answer.get('executed')
        assert client.post('/api/ai/copilot/ask',headers=staff,json={'message':'How do I submit an expense?'}).status_code==200

        rows=[{'title':'Leave request guidance v7','category':'Employee policy','content':'Staff may open the leave module and send a request for the approval workflow. The manager reviews the submitted request.',
               'feature_key':'leave','audience':'All'},
              {'title':'Confidential manager guide v7','category':'Management guide','content':'Managers should review requests in the assigned review queue and use authorized HRM workflows only.',
               'feature_key':'leave','audience':'Manager'}]
        payload={'rows':rows}
        assert client.post('/api/ai/copilot/knowledge/bulk/preview',json=payload).status_code==401
        assert client.post('/api/ai/copilot/knowledge/bulk/preview',headers=staff,json=payload).status_code==403
        assert client.post('/api/ai/copilot/knowledge/bulk/preview',headers=manager,json=payload).status_code==403
        wrong=client.post('/api/ai/copilot/knowledge/bulk/preview',headers=admin,json={'rows':[dict(rows[0],feature_key='not-a-feature') ]})
        assert wrong.status_code==422,wrong.text
        restricted=client.post('/api/ai/copilot/knowledge/bulk/preview',headers=admin,json={'rows':[dict(rows[0],feature_key='accounts',audience='All') ]})
        assert restricted.status_code==422,restricted.text
        duplicate=client.post('/api/ai/copilot/knowledge/bulk/preview',headers=admin,json={'rows':[rows[0],rows[0]]})
        assert duplicate.status_code==409,duplicate.text
        preview=client.post('/api/ai/copilot/knowledge/bulk/preview',headers=admin,json=payload)
        assert preview.status_code==200,preview.text
        view=preview.json()
        assert view['count']==2 and view['status']=='Draft' and view['requires_confirmation']
        assert 'content' not in str(view)
        assert client.post('/api/ai/copilot/knowledge/bulk/import',headers=admin,json={'rows':rows,'preview_token':view['preview_token']}).status_code==422
        altered=client.post('/api/ai/copilot/knowledge/bulk/import',headers=admin,json={
            'rows':[dict(rows[0],content='A different approved instruction that was not displayed to the reviewer.'),rows[1]],
            'preview_token':view['preview_token'],'confirm':'IMPORT_DRAFTS'})
        assert altered.status_code==403,altered.text
        badtoken=client.post('/api/ai/copilot/knowledge/bulk/import',headers=admin,json={
            'rows':rows,'preview_token':'1000.'+'a'*64,'confirm':'IMPORT_DRAFTS'})
        assert badtoken.status_code==409,badtoken.text
        with main.db() as c:
            assert c.execute('SELECT COUNT(*) FROM ai_knowledge_articles').fetchone()[0]==0
        saved=client.post('/api/ai/copilot/knowledge/bulk/import',headers=admin,json={
            'rows':rows,'preview_token':view['preview_token'],'confirm':'IMPORT_DRAFTS'})
        assert saved.status_code==201,saved.text
        assert saved.json()['created']==2 and saved.json()['status']=='Draft'
        with main.db() as c:
            drafts=c.execute('SELECT status,created_by FROM ai_knowledge_articles ORDER BY id').fetchall()
            assert len(drafts)==2 and all(row['status']=='Draft' for row in drafts)
            assert c.execute("SELECT COUNT(*) FROM audit_events WHERE action='ai.knowledge.bulk_import'").fetchone()[0]==1
        assert client.post('/api/ai/copilot/knowledge/bulk/import',headers=admin,json={
            'rows':rows,'preview_token':view['preview_token'],'confirm':'IMPORT_DRAFTS'}).status_code==409
        assert client.post('/api/ai/copilot/knowledge/bulk/preview',headers=admin,json=payload).status_code==409
        assert not any(x.get('title')==rows[0]['title'] for x in ai.evidence({'id':staff_id,'role':'employee'}))
        publish=client.patch(f"/api/ai/copilot/knowledge/{saved.json()['article_ids'][0]}/state",headers=admin,json={'status':'Published'})
        assert publish.status_code==200,publish.text
        staff_docs=ai.evidence({'id':staff_id,'role':'employee'})
        assert any(x.get('title')==rows[0]['title'] for x in staff_docs)
        assert not any(x.get('title')==rows[1]['title'] for x in staff_docs)
        print('PASS AI v7: own-record pending snapshot, draft-only CSV import, role gates, review binding, expiry, duplicate prevention, RAG publication')

"""SASS AI v6 isolated regression: natural-language action previews, RAG diversity, permissions.
No external provider or live database calls. Run: python ai_copilot_v6_test.py
"""
from __future__ import annotations
import os, sys, tempfile
from pathlib import Path
from unittest.mock import patch
os.environ.update(SASS_HRM_TESTING='1', DB_ENGINE='sqlite',
                  JWT_SECRET='ai-v6-isolated-test-secret-long-enough-for-jwt-2026',
                  AI_COPILOT_GENERATION='0', AI_API_KEY='')
from fastapi.testclient import TestClient

with tempfile.TemporaryDirectory() as tmp:
    os.environ['DATABASE_PATH'] = str(Path(tmp)/'v6.sqlite')
    import main, create_admin
    ai=main.ai_copilot
    with TestClient(main.app) as client:
        with patch.object(sys, 'argv', ['create_admin.py','--email','admin@example.test','--name','HR Admin','--code','ADM-V6','--location','Hyderabad']), patch.object(create_admin.getpass,'getpass',side_effect=['TestPasswordStrongV6!']*2):
            create_admin.main()
        with main.db() as c:
            c.execute('''INSERT INTO employees(code,name,email,role,designation,department,location,work_mode,join_date,password_hash,account_active)
                VALUES(?,?,?,?,?,?,?,?,?,?,1)''', ('ST-V6','Test Staff','staff@example.test','employee','Analyst','People','Hyderabad','Hybrid','2026-01-03',main.hash_password('StaffPasswordStrongV6!')))
        def auth(email, pw):
            r=client.post('/api/auth/login',json={'email':email,'password':pw})
            assert r.status_code==200,r.text
            return {'Authorization':'Bearer '+r.json()['token']}
        staff=auth('staff@example.test','StaffPasswordStrongV6!')
        admin=auth('admin@example.test','TestPasswordStrongV6!')
        checks={
            'please submit my leave request':'submit_leave',
            'apply for time off':'submit_leave',
            'create a support ticket':'submit_service_request',
            'I would like to check in today':'check_in',
            'How do I check out today?':'check_out',
            'please add my calendar event':'create_personal_event',
            'edit my calendar event':'edit_personal_event',
            'delete my calendar event':'delete_personal_event',
            'request a remote work arrangement':'request_work_mode',
            'cancel my work arrangement':'cancel_work_mode',
            'submit an expense claim':'submit_expense',
            'request attendance correction':'request_attendance_correction',
            'cancel attendance correction':'cancel_attendance_correction',
            'update my task status':'update_task_status',
            'mark this notification as read':'mark_notification_read',
            'change my date format':'update_my_preferences',
        }
        with main.db() as c:
            before=c.execute('SELECT COUNT(*) FROM ai_action_proposals').fetchone()[0]
        for question,expected in checks.items():
            response=client.post('/api/ai/copilot/ask',headers=staff,json={'message':question})
            assert response.status_code==200,(question,response.text)
            payload=response.json()
            assert payload['mode']=='action-guidance',(question,payload)
            assert payload['actions'][0]['operation']==expected,(question,payload)
            assert payload['executed'] is False and payload['requires_confirmation'] is True
            assert payload['features'],question
        with main.db() as c:
            after=c.execute('SELECT COUNT(*) FROM ai_action_proposals').fetchone()[0]
        assert before==after,'Chat suggestions must not create action proposals'
        response=client.post('/api/ai/copilot/ask',headers=admin,json={'message':'assign a task to an employee'})
        assert response.status_code==200 and response.json()['actions'][0]['operation']=='create_hr_task',response.text
        response=client.post('/api/ai/copilot/ask',headers=staff,json={'message':'assign a task to an employee'})
        assert response.status_code==200 and not any(a['operation']=='create_hr_task' for a in response.json().get('actions',[])),response.text
        assert client.post('/api/ai/copilot/ask',json={'message':'check in today'}).status_code==401
        assert not ai.suggest_reviewed_action('what is the annual leave allowance?',{'role':'employee','id':1})
        assert not ai.suggest_reviewed_action('delete another employee record',{'role':'admin','id':1})
        assert not ai.suggest_reviewed_action('do not check in yet',{'role':'employee','id':1})
        assert not ai.suggest_reviewed_action('what is check-in?',{'role':'employee','id':1})
        docs=[{'kind':'knowledge','id':'11','title':'Leave approval','text':f'Leave approval process and steps {i}'} for i in range(8)]
        docs += [{'kind':'knowledge','id':'12','title':'Leave form','text':'Leave request approval form and steps'},
                 {'kind':'feature','id':'leave','title':'Leave workflow','text':'Leave approval and steps'}]
        picked=ai.diverse_rank('leave approval',docs,6)
        assert len([d for d in picked if d.get('id')=='11'])<=2,picked
        assert any(d.get('id')=='12' for d in picked),picked
        caps=client.get('/api/ai/copilot/capabilities',headers=staff).json()
        assert caps['natural_language_action_hints'] and caps['rag_source_diversity']
print('PASS AI v6: 16 action intents, role checks, no unconfirmed writes, 401 checks, diverse RAG')

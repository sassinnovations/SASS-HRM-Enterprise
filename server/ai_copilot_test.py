"""Isolated integration coverage of SASS AI navigation, RAG, confirmed writes and access checks.

No live MySQL, public LLM provider or production HR records are contacted.
"""
from __future__ import annotations

import os
import sys
import tempfile
from datetime import date, timedelta
from pathlib import Path
from unittest.mock import patch

os.environ.update(SASS_HRM_TESTING='1', DB_ENGINE='sqlite', JWT_SECRET='ai-copilot-iso-test-only-random-secret-very-long-001', AI_COPILOT_GENERATION='0')
from fastapi.testclient import TestClient

with tempfile.TemporaryDirectory() as tmp:
    os.environ['DATABASE_PATH'] = str(Path(tmp) / 'ai_test.sqlite')
    import main
    import create_admin
    with TestClient(main.app) as client:
        with patch.object(sys, 'argv', ['create_admin.py', '--email', 'hr@example.test', '--name', 'HR Test', '--code', 'SA-TEST', '--location', 'Hyderabad']), patch.object(create_admin.getpass, 'getpass', side_effect=['SuperSecureTestPassword123!'] * 2):
            create_admin.main()
        def login(email: str, password: str) -> dict:
            response = client.post('/api/auth/login', json={'email': email, 'password': password})
            assert response.status_code == 200, response.text
            return {'Authorization': 'Bearer ' + response.json()['token']}
        admin = login('hr@example.test', 'SuperSecureTestPassword123!')
        with main.db() as conn:
            for code, email in [('STAFF-A', 'a@example.test'), ('STAFF-B', 'b@example.test')]:
                conn.execute('''INSERT INTO employees(code,name,email,role,designation,department,location,work_mode,join_date,password_hash,account_active)
                                VALUES(?,?,?,?,?,?,?,?,?,?,1)''', (code, code, email, 'employee', 'Analyst', 'Operations', 'Hyderabad', 'Hybrid', '2025-01-01', main.hash_password('StaffTestPassword123!')))
            a_id = conn.execute("SELECT id FROM employees WHERE code='STAFF-A'").fetchone()[0]
            b_id = conn.execute("SELECT id FROM employees WHERE code='STAFF-B'").fetchone()[0]
            conn.execute("INSERT INTO leave_entitlements(leave_type,days,updated_at) VALUES('Annual Leave',24,'2026-11-24')")
            conn.execute('INSERT INTO policies(title,category,content,last_updated) VALUES(?,?,?,?)', ('Remote work', 'Workplace', 'Remote work requires manager approval and compliance with company security standards.', '2026-11-24'))
        a = login('a@example.test', 'StaffTestPassword123!')
        b = login('b@example.test', 'StaffTestPassword123!')
        def get(path: str, headers: dict):
            return client.get('/api' + path, headers=headers)
        def post(path: str, data: dict, headers: dict):
            return client.post('/api' + path, headers=headers, json=data)
        assert get('/ai/copilot/features', {}).status_code == 401
        admin_features = get('/ai/copilot/features', admin).json()
        employee_features = get('/ai/copilot/features', a).json()
        assert len(main.ai_copilot.catalog()) == 73
        assert len(admin_features) == 72, len(admin_features)
        assert len(employee_features) < len(admin_features)
        assert 'accounts' not in {x['key'] for x in employee_features}
        assert 'recruitment' not in {x['key'] for x in employee_features}
        assert 'employees' in {x['key'] for x in employee_features}
        assert 'developer' not in {x['key'] for x in admin_features}  # Separate developer grant required.
        with main.db() as conn:
            admin_id = conn.execute("SELECT id FROM employees WHERE email='hr@example.test'").fetchone()[0]
            conn.execute('INSERT INTO developer_grants(employee_id,enabled,granted_at) VALUES(?,?,?)',(admin_id,1,'2026-11-24'))
        assert len(get('/ai/copilot/features', admin).json()) == 73
        cap = get('/ai/copilot/capabilities', a).json()
        assert cap['mode'] == 'lexical-rag' and cap['private_records_sent_to_llm'] is False
        assert len(cap['confirmed_actions']) == 15 and {'submit_leave','submit_service_request','check_in','check_out','create_personal_event','edit_personal_event','delete_personal_event','request_work_mode','cancel_work_mode','submit_expense','request_attendance_correction','cancel_attendance_correction','update_task_status','mark_notification_read','update_my_preferences'} == set(cap['confirmed_actions'])
        # Approved policy becomes retrievable with citation; never leak sensitive drafts.
        pol = post('/ai/copilot/ask', {'message': 'What does remote work require?'}, a)
        assert pol.status_code == 200, pol.text
        assert any(s['kind'] == 'policy' for s in pol.json()['sources']), pol.json()
        new = {'title': 'Office travel process', 'category': 'Travel', 'content': 'Book authorized travel only after your manager has approved the travel request. Expenses require an itemized receipt.', 'status': 'Draft'}
        assert post('/ai/copilot/knowledge', new, a).status_code == 403
        saved = post('/ai/copilot/knowledge', new, admin)
        assert saved.status_code == 201, saved.text
        knowledge_id = saved.json()['id']
        assert get('/ai/copilot/knowledge', a).status_code == 403
        assert get(f'/ai/copilot/knowledge/{knowledge_id}', a).status_code == 403
        assert not any(s['kind'] == 'knowledge' for s in post('/ai/copilot/ask', {'message':'itemized receipt travel process'}, a).json()['sources'])
        state = client.patch(f'/api/ai/copilot/knowledge/{knowledge_id}/state', headers=admin, json={'status':'Published'})
        assert state.status_code == 200
        published = post('/ai/copilot/ask', {'message':'How do I get an itemized receipt for travel?'}, a).json()
        assert any(s['kind'] == 'knowledge' for s in published['sources']), published
        assert client.delete(f'/api/ai/copilot/knowledge/{knowledge_id}', headers=a).status_code == 403
        assert client.delete(f'/api/ai/copilot/knowledge/{knowledge_id}', headers=admin).json()['unpublished']
        assert not any(s['kind'] == 'knowledge' for s in post('/ai/copilot/ask', {'message':'itemized receipt travel process'}, a).json()['sources'])
        # Navigation searches respect role boundaries and cannot leak private records.
        employee_ats = post('/ai/copilot/ask', {'message':'Where is the candidate database ATS?'}, a).json()
        assert not any(s['url'].startswith('/talent/candidate-search') for s in employee_ats['sources'])
        admin_ats = post('/ai/copilot/ask', {'message':'Where is the candidate database ATS?'}, admin).json()
        assert any(s['kind'] == 'feature' and s['id'] == 'candidatesearch' for s in admin_ats['sources']), admin_ats
        guard = post('/ai/copilot/ask', {'message':'What is other employee salary of Bob?'}, a).json()
        assert guard['mode'] == 'guardrail' and not guard['sources']
        # Own data results are scoped to the authenticated employee; not account supplied in prompt.
        with main.db() as conn:
            conn.execute("INSERT INTO service_categories(name,description,active) VALUES('Employment letter','Request HR letter',1)")
            cid = conn.execute("SELECT id FROM service_categories WHERE name='Employment letter'").fetchone()[0]
        request_params = {'category_id':cid,'subject':'Please provide an employment letter','details':'Please issue my approved employment letter for visa paperwork.'}
        prepared = post('/ai/copilot/actions/prepare', {'operation':'submit_service_request','parameters':request_params}, a)
        assert prepared.status_code == 201, prepared.text
        proposal = prepared.json()['proposal_id']
        assert len(get('/ai/copilot/features', a).json()) > 10
        assert post(f'/ai/copilot/actions/{proposal}/confirm', {'confirm':'CONFIRM'}, b).status_code == 404
        assert post(f'/ai/copilot/actions/{proposal}/confirm', {'confirm':'yes'}, a).status_code == 422
        with main.db() as conn:
            assert conn.execute('SELECT COUNT(*) FROM service_requests').fetchone()[0] == 0
        executed = post(f'/ai/copilot/actions/{proposal}/confirm', {'confirm':'CONFIRM'}, a)
        assert executed.status_code == 200, executed.text
        assert executed.json()['state'] == 'Executed'
        assert post(f'/ai/copilot/actions/{proposal}/confirm', {'confirm':'CONFIRM'}, a).status_code == 409
        with main.db() as conn:
            req = conn.execute('SELECT employee_id FROM service_requests ORDER BY id DESC LIMIT 1').fetchone()
            assert req['employee_id'] == a_id != b_id
            assert conn.execute("SELECT COUNT(*) FROM audit_events WHERE action='ai.action.confirmed'").fetchone()[0] == 1
        own = post('/ai/copilot/ask', {'message':'What is my service request status?'}, a).json()
        assert 'employment letter' in own['answer'].lower(), own
        other = post('/ai/copilot/ask', {'message':'What is my service request status?'}, b).json()
        assert 'no Request Desk requests' in other['answer']
        # New personal record lookups use the authenticated actor, not a supplied employee ID.
        with main.db() as conn:
            conn.execute('INSERT INTO hr_tasks(title,assignee_id,created_by,due_date,priority,status,created_at) VALUES(?,?,?,?,?,?,?)',
                         ('Complete onboarding checklist',a_id,a_id,'2026-12-10','Normal','Open','2026-11-24'))
            conn.execute('INSERT INTO hr_tasks(title,assignee_id,created_by,due_date,priority,status,created_at) VALUES(?,?,?,?,?,?,?)',
                         ('Confidential second employee task',b_id,b_id,'2026-12-10','Normal','Open','2026-11-24'))
            conn.execute('INSERT INTO goals(employee_id,title,description,due_date,progress,status) VALUES(?,?,?,?,?,?)',
                         (a_id,'Learn data engineering','Improve ETL knowledge','2027-06-01',30,'In Progress'))
        for head, expect, not_expect in [(a,'Complete onboarding checklist','Confidential second employee task'),
                                         (b,'Confidential second employee task','Complete onboarding checklist')]:
            tasks = post('/ai/copilot/ask', {'message':'Show my tasks'}, head).json()
            assert tasks['mode']=='data-backed' and expect in tasks['answer'] and not_expect not in tasks['answer'], tasks
        own_goals = post('/ai/copilot/ask', {'message':'Show my goals'}, a).json()
        assert own_goals['mode']=='data-backed' and 'Learn data engineering' in own_goals['answer'], own_goals
        other_goals = post('/ai/copilot/ask', {'message':'Show my goals'}, b).json()
        assert 'No performance goals' in other_goals['answer'], other_goals
        # Smoke-test all other owner-scoped SQL readers against the existing schema.
        for phrase in ('my training', 'my benefits', 'my helpdesk tickets', 'my expenses',
                       'my assets', 'my timesheets', 'my skills', 'my onboarding',
                       'my career plan', 'my work arrangement', 'my attendance correction',
                       'my document vault', 'my unread policy acknowledgements'):
            result = post('/ai/copilot/ask', {'message': phrase}, a)
            assert result.status_code == 200, (phrase, result.status_code, result.text)
            assert result.json()['mode'] == 'data-backed', (phrase, result.json())
        # Review/cancel and expiry do not create records.
        to_cancel = post('/ai/copilot/actions/prepare', {'operation':'submit_service_request','parameters':request_params}, b).json()['proposal_id']
        assert client.post('/api/ai/copilot/actions/'+to_cancel+'/cancel', headers=b).status_code == 200
        assert post(f'/ai/copilot/actions/{to_cancel}/confirm', {'confirm':'CONFIRM'}, b).status_code == 409
        expired = post('/ai/copilot/actions/prepare', {'operation':'submit_service_request','parameters':request_params}, b).json()['proposal_id']
        with main.db() as conn:
            conn.execute('UPDATE ai_action_proposals SET expires_at=? WHERE id=?', ('2000-01-01T00:00:00+00:00', expired))
        assert post(f'/ai/copilot/actions/{expired}/confirm', {'confirm':'CONFIRM'}, b).status_code == 410
        # Create an own leave request and honor the original leave workflow validation.
        start = (date.today() + timedelta(days=8)).isoformat()
        end = (date.today() + timedelta(days=9)).isoformat()
        params = {'start_date':start,'end_date':end,'leave_type':'Annual Leave','reason':'Family appointment'}
        invalid = post('/ai/copilot/actions/prepare', {'operation':'submit_leave','parameters':{**params,'start_date':'not-a-date'}}, a)
        assert invalid.status_code == 422, invalid.text
        leave_proposal = post('/ai/copilot/actions/prepare', {'operation':'submit_leave','parameters':params}, a)
        assert leave_proposal.status_code == 201, leave_proposal.text
        leave_confirmation = post('/ai/copilot/actions/'+leave_proposal.json()['proposal_id']+'/confirm', {'confirm':'CONFIRM'}, a)
        assert leave_confirmation.status_code == 200, leave_confirmation.text
        with main.db() as conn:
            row = conn.execute('SELECT employee_id FROM leave_requests WHERE status=?', ('Pending',)).fetchone()
            assert row and row['employee_id'] == a_id
        assert 'estimated remaining' in post('/ai/copilot/ask', {'message':'What is my leave balance?'}, a).json()['answer'].lower()
        # Expanded feature control: all accessible features have a guide, with reviewed actions
        # mapped to owning feature IDs, not arbitrary routes selected by chat content.
        # Every allowed module has a read-only API/SQL linkage probe. No row contents are returned.
        scan = get('/ai/copilot/integrations', a)
        assert scan.status_code == 200, scan.text
        scan_json = scan.json()
        assert scan_json['feature_count'] == len(employee_features)
        assert {x['feature_key'] for x in scan_json['items']} == {x['key'] for x in employee_features}
        assert not any('employees' in x or 'password_hash' in x for x in scan_json['items'])
        assert get('/ai/copilot/integrations', {}).status_code == 401
        admin_scan = get('/ai/copilot/integrations', admin).json()
        print('Feature schema probes: admin',admin_scan['ready'],'/',admin_scan['feature_count'], 'employee',scan_json['ready'],'/',scan_json['feature_count'])
        print('Unready:', [(item['feature_key'],item['api_registered'],item['tables_accessible'],item['tables_mapped']) for item in admin_scan['items'] if item['status']!='ready'])
        assert 'accounts' in {x['feature_key'] for x in admin_scan['items']}
        assert 'accounts' not in {x['feature_key'] for x in scan_json['items']}
        contextual = post('/ai/copilot/ask', {'message':'How do I use this page?','feature_key':'leave'}, a)
        assert contextual.status_code == 200, contextual.text
        assert any(x['kind']=='feature' and x['id']=='leave' for x in contextual.json()['sources']),contextual.json()
        command = post('/ai/copilot/ask', {'message':'open Employee HRIS'}, a)
        assert command.status_code == 200 and command.json()['mode']=='feature-command', command.text
        assert command.json()['features'][0]['key']=='employees'
        protected = post('/ai/copilot/ask', {'message':'open Account provisioning'}, a)
        assert not any(x['key']=='accounts' for x in protected.json().get('features',[])), protected.json()
        # Owner-only notification action cannot be prepared using someone else's record.
        with main.db() as conn:
            conn.execute('INSERT INTO notifications(employee_id,title,body,is_read,created_at) VALUES(?,?,?,?,?)',(a_id,'Own notification','Hello',0,'2026-11-24'))
            a_notice=conn.execute('SELECT MAX(id) FROM notifications WHERE employee_id=?',(a_id,)).fetchone()[0]
            conn.execute('INSERT INTO notifications(employee_id,title,body,is_read,created_at) VALUES(?,?,?,?,?)',(b_id,'Other notification','Hello',0,'2026-11-24'))
            b_notice=conn.execute('SELECT MAX(id) FROM notifications WHERE employee_id=?',(b_id,)).fetchone()[0]
        assert post('/ai/copilot/actions/prepare',{'operation':'mark_notification_read','parameters':{'notification_id':b_notice}},a).status_code==404, post('/ai/copilot/actions/prepare',{'operation':'mark_notification_read','parameters':{'notification_id':b_notice}},a).text
        notice=post('/ai/copilot/actions/prepare',{'operation':'mark_notification_read','parameters':{'notification_id':a_notice}},a)
        assert notice.status_code==201,notice.text
        assert post(f'/ai/copilot/actions/{notice.json()["proposal_id"]}/confirm',{'confirm':'CONFIRM'},a).status_code==200
        assert post('/ai/copilot/actions/prepare',{'operation':'mark_notification_read','parameters':{'notification_id':a_notice}},a).status_code==409
        pref=post('/ai/copilot/actions/prepare',{'operation':'update_my_preferences','parameters':{'date_format':'YYYY-MM-DD','density':'Compact','reduce_motion':True}},a)
        assert pref.status_code==201,pref.text
        assert post(f'/ai/copilot/actions/{pref.json()["proposal_id"]}/confirm',{'confirm':'CONFIRM'},a).status_code==200
        assert get('/me/preferences',a).json()['density']=='Compact'
        assert get('/me/preferences',b).json()['density']=='Comfortable'
        stale_pref = post('/ai/copilot/actions/prepare',{'operation':'update_my_preferences','parameters':{'date_format':'MM/DD/YYYY','density':'Comfortable','reduce_motion':False}},a)
        assert stale_pref.status_code==201
        # Changing preferences outside the copilot must invalidate its old confirmation.
        outside = client.put('/api/me/preferences',headers=a,json={'date_format':'YYYY-MM-DD','density':'Comfortable','reduce_motion':True})
        assert outside.status_code==200,outside.text
        assert post(f'/ai/copilot/actions/{stale_pref.json()["proposal_id"]}/confirm',{'confirm':'CONFIRM'},a).status_code==409
        assert get('/me/preferences',a).json()['date_format']=='YYYY-MM-DD'
        action_map = get('/ai/copilot/actions/catalog', a)
        assert action_map.status_code == 200, action_map.text
        assert len(action_map.json()) == 15
        assert not any(item['effect']=='delete' and item['feature']!='calendar' for item in action_map.json())
        for feature in get('/ai/copilot/features', a).json():
            r = get('/ai/copilot/features/'+feature['key']+'/guide', a)
            assert r.status_code == 200, (feature['key'], r.text)
            assert r.json()['key'] == feature['key']
        assert get('/ai/copilot/features/accounts/guide', a).status_code == 404
        assert get('/ai/copilot/features/unknown/guide', admin).status_code == 404
        assert get('/ai/copilot/actions/my-options', {}).status_code == 401
        assert get('/ai/copilot/health', a).status_code == 403
        health = get('/ai/copilot/health', admin)
        assert health.status_code == 200, health.text
        assert health.json()['inventoried_features'] == 73 and health.json()['confirmed_action_types'] == 31
        assert health.json()['vector_search_enabled'] is False and health.json()['private_records_sent_to_llm'] is False
        options_a = get('/ai/copilot/actions/my-options', a).json()
        assert options_a['personal_events']==[] and options_a['pending_work_mode']==[] and options_a['pending_corrections']==[] and options_a['assignable_staff']==[], options_a
        # Attendance check-in and checkout use existing company-timezone HRM handlers.
        assert post('/ai/copilot/actions/prepare', {'operation':'check_in','parameters':{'employee_id':b_id}}, a).status_code == 422
        pin = post('/ai/copilot/actions/prepare', {'operation':'check_in','parameters':{}}, a)
        assert pin.status_code == 201, pin.text
        assert post('/ai/copilot/actions/'+pin.json()['proposal_id']+'/confirm', {'confirm':'CONFIRM'}, a).status_code == 200
        duplicate = post('/ai/copilot/actions/prepare', {'operation':'check_in','parameters':{}}, a).json()['proposal_id']
        assert post('/ai/copilot/actions/'+duplicate+'/confirm', {'confirm':'CONFIRM'}, a).status_code == 409
        pout = post('/ai/copilot/actions/prepare', {'operation':'check_out','parameters':{}}, a).json()['proposal_id']
        assert post('/ai/copilot/actions/'+pout+'/confirm', {'confirm':'CONFIRM'}, a).status_code == 200
        with main.db() as conn:
            aa = conn.execute('SELECT employee_id,check_in,check_out FROM attendance WHERE employee_id=? ORDER BY id DESC LIMIT 1',(a_id,)).fetchone()
            assert aa and aa['check_in'] and aa['check_out'] and aa['employee_id']==a_id
            assert conn.execute('SELECT COUNT(*) FROM attendance WHERE employee_id=?',(b_id,)).fetchone()[0] == 0
        # Personal calendar creates, updates, and deletes only the requesting owner's event.
        cal = {'day':(date.today()+timedelta(days=4)).isoformat(),'start_time':'10:15','title':'My personal meeting','notes':'Planning'}
        pcal = post('/ai/copilot/actions/prepare', {'operation':'create_personal_event','parameters':cal}, a)
        assert pcal.status_code == 201, pcal.text
        created = post('/ai/copilot/actions/'+pcal.json()['proposal_id']+'/confirm', {'confirm':'CONFIRM'}, a)
        assert created.status_code == 200, created.text
        eid = created.json()['result']['id']
        assert any(x['id']==eid for x in get('/ai/copilot/actions/my-options', a).json()['personal_events'])
        assert not any(x['id']==eid for x in get('/ai/copilot/actions/my-options', b).json()['personal_events'])
        bad_edit = post('/ai/copilot/actions/prepare', {'operation':'edit_personal_event','parameters':{**cal,'event_id':eid,'title':'Intruder'}}, b)
        assert bad_edit.status_code == 404, bad_edit.text
        bad_delete = post('/ai/copilot/actions/prepare', {'operation':'delete_personal_event','parameters':{'event_id':eid}}, b)
        assert bad_delete.status_code == 404, bad_delete.text
        # In-flight edits made after review invalidate an existing delete proposal.
        stale = post('/ai/copilot/actions/prepare', {'operation':'delete_personal_event','parameters':{'event_id':eid}}, a).json()['proposal_id']
        edit = post('/ai/copilot/actions/prepare', {'operation':'edit_personal_event','parameters':{**cal,'event_id':eid,'title':'My updated event'}}, a)
        assert edit.status_code == 201, edit.text
        assert post('/ai/copilot/actions/'+edit.json()['proposal_id']+'/confirm', {'confirm':'CONFIRM'}, a).status_code == 200
        assert post('/ai/copilot/actions/'+stale+'/confirm', {'confirm':'CONFIRM'}, a).status_code == 409
        with main.db() as conn:
            assert conn.execute('SELECT title FROM personal_calendar_events WHERE id=?',(eid,)).fetchone()['title']=='My updated event'
        correct = post('/ai/copilot/actions/prepare', {'operation':'delete_personal_event','parameters':{'event_id':eid}}, a).json()['proposal_id']
        assert post('/ai/copilot/actions/'+correct+'/confirm', {'confirm':'CONFIRM'}, a).status_code == 200
        with main.db() as conn:
            assert conn.execute('SELECT id FROM personal_calendar_events WHERE id=?',(eid,)).fetchone() is None
        # Work-mode requests require ordinary HR approval, and only the requester can cancel.
        pwork = post('/ai/copilot/actions/prepare', {'operation':'request_work_mode','parameters':{'requested_mode':'Remote','reason':'Temporary personal arrangement','effective_date':(date.today()+timedelta(days=8)).isoformat()}}, a)
        assert pwork.status_code == 201, pwork.text
        work = post('/ai/copilot/actions/'+pwork.json()['proposal_id']+'/confirm', {'confirm':'CONFIRM'}, a)
        assert work.status_code == 200, work.text
        wid = work.json()['result']['id']
        assert any(x['id']==wid for x in get('/ai/copilot/actions/my-options', a).json()['pending_work_mode'])
        assert not any(x['id']==wid for x in get('/ai/copilot/actions/my-options', b).json()['pending_work_mode'])
        assert post('/ai/copilot/actions/prepare', {'operation':'cancel_work_mode','parameters':{'request_id':wid}}, b).status_code == 404
        cancel_work = post('/ai/copilot/actions/prepare', {'operation':'cancel_work_mode','parameters':{'request_id':wid}}, a).json()['proposal_id']
        assert post('/ai/copilot/actions/'+cancel_work+'/confirm', {'confirm':'CONFIRM'}, a).status_code == 200
        with main.db() as conn:
            mode = conn.execute('SELECT status,employee_id FROM work_mode_requests WHERE id=?',(wid,)).fetchone()
            assert mode['status']=='Cancelled' and mode['employee_id']==a_id
        assert post('/ai/copilot/actions/prepare', {'operation':'cancel_work_mode','parameters':{'request_id':wid}}, a).status_code == 409
        action_chat = post('/ai/copilot/ask', {'message':'Where is the attendance check-in feature?'}, a).json()
        assert any(item['operation']=='check_in' for item in action_chat.get('actions',[])), action_chat
        # A chat suggestion is only a link to the review form; it never creates or mutates anything.
        # v3: all 73 registered feature pages support role-scoped control plans,
        # without claiming all their CRUD methods are executable by AI.
        for feature in get('/ai/copilot/features', admin).json():
            for intent in ('view','create','edit','delete','settings','help'):
                plan = post('/ai/copilot/control/plan', {'feature_key':feature['key'],'intent':intent}, admin)
                assert plan.status_code == 200, (feature['key'],intent,plan.text)
                assert plan.json()['executed'] is False and plan.json()['target_key']
        assert post('/ai/copilot/control/plan', {'feature_key':'accounts','intent':'delete'}, a).status_code == 404
        assert post('/ai/copilot/control/plan', {'feature_key':'__unknown__','intent':'edit'}, admin).status_code == 404
        assert post('/ai/copilot/control/plan', {'feature_key':'employees','intent':'execute_sql'}, admin).status_code == 422
        # v3: RAG audience + feature scopes prevent cross-role disclosure even when published.
        restricted = {'title':'Admin-only account procedures','category':'Admin guidance',
                      'content':'Internal admin account recovery keyword ORCHID-77. Use only the dedicated security admin page.',
                      'feature_key':'accounts','audience':'Admin','status':'Published'}
        invalid_scope = post('/ai/copilot/knowledge', {**restricted,'audience':'All'}, admin)
        assert invalid_scope.status_code == 422,invalid_scope.text
        admin_doc = post('/ai/copilot/knowledge', restricted, admin)
        assert admin_doc.status_code == 201,admin_doc.text
        assert any(s['kind']=='knowledge' and s['id']==str(admin_doc.json()['id'])
                   for s in post('/ai/copilot/ask', {'message':'ORCHID-77 account recovery'},admin).json()['sources'])
        assert not any(s['kind']=='knowledge' and s['id']==str(admin_doc.json()['id'])
                       for s in post('/ai/copilot/ask', {'message':'ORCHID-77 account recovery'},a).json()['sources'])
        guide = get('/ai/copilot/features/accounts/guide', admin)
        assert any(x['id']==admin_doc.json()['id'] for x in guide.json()['knowledge'])
        assert get('/ai/copilot/features/accounts/guide',a).status_code==404
        assert get(f'/ai/copilot/knowledge/{admin_doc.json()["id"]}',admin).json()['audience']=='Admin'
        # Employee cannot use the manager-only task creation control.
        assert post('/ai/copilot/actions/prepare', {'operation':'create_hr_task','parameters':{}},a).status_code==403
        assert not any(x['operation']=='create_hr_task' for x in get('/ai/copilot/actions/catalog',a).json())
        assert any(x['operation']=='create_hr_task' for x in get('/ai/copilot/actions/catalog',admin).json())
        create_args = {'title':'Complete AI audit verification','assignee_id':a_id,
                       'due_date':(date.today()+timedelta(days=12)).isoformat(),'priority':'Normal'}
        item = post('/ai/copilot/actions/prepare',{'operation':'create_hr_task','parameters':create_args},admin)
        assert item.status_code==201,item.text
        inserted=post('/ai/copilot/actions/'+item.json()['proposal_id']+'/confirm',{'confirm':'CONFIRM'},admin)
        assert inserted.status_code==200,inserted.text
        task_id=inserted.json()['result']['id']
        assert any(t['id']==task_id for t in get('/ai/copilot/actions/my-options',a).json()['my_tasks'])
        assert not any(t['id']==task_id for t in get('/ai/copilot/actions/my-options',b).json()['my_tasks'])
        assert post('/ai/copilot/actions/prepare',{'operation':'update_task_status','parameters':{'task_id':task_id,'status':'Completed'}},b).status_code==404
        taskp=post('/ai/copilot/actions/prepare',{'operation':'update_task_status','parameters':{'task_id':task_id,'status':'In Progress'}},a)
        assert taskp.status_code==201,taskp.text
        assert post('/ai/copilot/actions/'+taskp.json()['proposal_id']+'/confirm',{'confirm':'CONFIRM'},a).status_code==200
        stale_task=post('/ai/copilot/actions/prepare',{'operation':'update_task_status','parameters':{'task_id':task_id,'status':'Open'}},a).json()['proposal_id']
        assert client.patch('/api/tasks/'+str(task_id),headers=admin,json={'status':'Completed'}).status_code==200
        assert post('/ai/copilot/actions/'+stale_task+'/confirm',{'confirm':'CONFIRM'},a).status_code==409
        # Expense submission goes through normal policy limits and persists only for actor.
        exp_params={'title':'Office consumables','amount':120.50,'category':'Other',
                    'business_purpose':'Office supplies purchase','merchant':'Office supplier',
                    'receipt_reference':'TEST-RECEIPT-1'}
        exp_p=post('/ai/copilot/actions/prepare',{'operation':'submit_expense','parameters':exp_params},a)
        assert exp_p.status_code==201,exp_p.text
        saved_exp=post('/ai/copilot/actions/'+exp_p.json()['proposal_id']+'/confirm',{'confirm':'CONFIRM'},a)
        assert saved_exp.status_code==200,saved_exp.text
        with main.db() as conn:
            ex=conn.execute('SELECT employee_id,status FROM expenses WHERE id=?',(saved_exp.json()['result']['id'],)).fetchone()
            assert ex['employee_id']==a_id and ex['status']=='Pending'
        # Correction submission/cancellation remains owner-scoped.
        corr_params={'work_day':(date.today()-timedelta(days=1)).isoformat(),
                     'proposed_in':'09:00','proposed_out':'18:00','reason':'Fingerprint reader did not register my punch'}
        corrp=post('/ai/copilot/actions/prepare',{'operation':'request_attendance_correction','parameters':corr_params},a)
        assert corrp.status_code==201,corrp.text
        saved_corr=post('/ai/copilot/actions/'+corrp.json()['proposal_id']+'/confirm',{'confirm':'CONFIRM'},a)
        assert saved_corr.status_code==200,saved_corr.text
        corr_id=saved_corr.json()['result']['id']
        assert any(r['id']==corr_id for r in get('/ai/copilot/actions/my-options',a).json()['pending_corrections'])
        assert post('/ai/copilot/actions/prepare',{'operation':'cancel_attendance_correction','parameters':{'correction_id':corr_id}},b).status_code==404
        cancelp=post('/ai/copilot/actions/prepare',{'operation':'cancel_attendance_correction','parameters':{'correction_id':corr_id}},a)
        assert cancelp.status_code==201,cancelp.text
        assert post('/ai/copilot/actions/'+cancelp.json()['proposal_id']+'/confirm',{'confirm':'CONFIRM'},a).status_code==200
        with main.db() as conn:
            assert conn.execute('SELECT status FROM attendance_corrections WHERE id=?',(corr_id,)).fetchone()['status']=='Cancelled'
        print('PASS SASS AI v3: all 73 feature plans, role-filtered feature RAG, 16 confirmed actions, expenses, HR tasks, attendance corrections, owner scope, stale guards and auditing')

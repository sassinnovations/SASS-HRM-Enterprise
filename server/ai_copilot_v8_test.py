"""Isolated v8 tests: all-feature command planning, playbook access and safe no-op semantics.
Run python server/ai_copilot_v8_test.py. Never contacts production MySQL or an AI provider.
"""
from __future__ import annotations
import os, sys, tempfile
from pathlib import Path
from unittest.mock import patch

os.environ.update(SASS_HRM_TESTING='1', DB_ENGINE='sqlite',
                  JWT_SECRET='long-test-secret-for-ai-v8-command-workbench-2026',
                  AI_COPILOT_GENERATION='0',AI_API_KEY='')
from fastapi.testclient import TestClient
with tempfile.TemporaryDirectory() as root:
    os.environ['DATABASE_PATH'] = str(Path(root)/'test.sqlite')
    import main, create_admin
    from ai_copilot import catalog
    with TestClient(main.app) as client:
        with patch.object(sys,'argv',['create_admin.py','--email','hr@example.test','--name','Admin','--code','ADMIN8','--location','Hyderabad']), \
             patch.object(create_admin.getpass,'getpass',side_effect=['StrongAdminPasswordV8!']*2):
            create_admin.main()
        with main.db() as c:
            c.execute('''INSERT INTO employees(code,name,email,role,designation,department,location,work_mode,join_date,password_hash,account_active)
                VALUES(?,?,?,?,?,?,?,?,?,?,1)''',('STAFF8','Employee','staff@example.test','employee','Analyst','Operations','Hyderabad','Hybrid','2026-01-01',main.hash_password('StrongStaffPasswordV8!')))
        def login(email,password):
            r=client.post('/api/auth/login',json={'email':email,'password':password})
            assert r.status_code==200,r.text
            return {'Authorization':'Bearer '+r.json()['token']}
        admin=login('hr@example.test','StrongAdminPasswordV8!')
        staff=login('staff@example.test','StrongStaffPasswordV8!')
        endpoint='/api/ai/copilot/commands/preview'
        assert client.post(endpoint,json={'command':'Edit Employee HRIS'}).status_code==401
        assert client.get('/api/ai/copilot/workflows').status_code==401
        assert len(catalog())==73
        # Every authorized module has an operation plan; even developer is protected.
        admin_features=client.get('/api/ai/copilot/features',headers=admin).json()
        staff_features=client.get('/api/ai/copilot/features',headers=staff).json()
        assert len(admin_features)==72 and len(staff_features)<72
        for row in admin_features:
            r=client.post(endpoint,headers=admin,json={'command':'Edit '+row['key']})
            assert r.status_code==200,(row['key'],r.text)
            obj=r.json()
            assert obj['status']=='matched' and obj['plans'][0]['feature_key']==row['key'],(row['key'],obj)
            assert obj['executed'] is False and obj['plans'][0]['executed'] is False
        with main.db() as c:
            admin_id=c.execute("SELECT id FROM employees WHERE email='hr@example.test'").fetchone()[0]
            c.execute('INSERT INTO developer_grants(employee_id,enabled,granted_at) VALUES(?,?,?)',(admin_id,1,'2026-11-25'))
        assert len(client.get('/api/ai/copilot/features',headers=admin).json())==73
        developer_plan=client.post(endpoint,headers=admin,json={'command':'Edit developer'})
        assert developer_plan.status_code==200 and developer_plan.json()['plans'][0]['feature_key']=='developer'
        # No escalation by saying an admin-only feature name or selecting it as context.
        denied=client.post(endpoint,headers=staff,json={'command':'Delete accounts','feature_key':'accounts'})
        assert denied.status_code==200 and denied.json()['status']=='not_found' and not denied.json()['plans']
        assert 'Account provisioning' not in str(denied.json())
        denied_chat=client.post('/api/ai/copilot/ask',headers=staff,json={'message':'Edit accounts'})
        assert denied_chat.status_code==200
        assert 'Account provisioning' not in str(denied_chat.json())
        # Declared DELETE methods are never presented as permission to execute deletion.
        plan=client.post(endpoint,headers=admin,json={'command':'Delete Employee HRIS'}).json()
        assert plan['status']=='matched' and not plan['plans'][0]['approved_actions']
        assert plan['plans'][0]['executed'] is False
        assert 'existing authorized screen' in plan['plans'][0]['guidance'].lower() or 'source inventory' in plan['plans'][0]['guidance'].lower()
        settings=client.post(endpoint,headers=admin,json={'command':'Settings for Employee HRIS'}).json()
        assert settings['status']=='matched' and settings['plans'][0]['target_key']
        invalid=client.post(endpoint,headers=staff,json={'command':'Make me CEO without approval'}).json()
        assert invalid['status']=='unrecognized' and invalid['executed'] is False
        assert client.post(endpoint,headers=staff,json={'command':'x'}).status_code==422
        assert client.post(endpoint,headers=staff,json={'command':'x'*401}).status_code==422
        chat=client.post('/api/ai/copilot/ask',headers=admin,json={'message':'Edit Employee HRIS'}).json()
        assert chat['mode']=='feature-plan' and chat['executed'] is False
        assert chat['features'][0]['key']=='employees'
        assert 'No changes have been made.' in chat['answer']
        # Reviewer-approved personal action stays in the existing secure form.
        own_action=client.post('/api/ai/copilot/ask',headers=staff,json={'message':'Submit my leave request'}).json()
        assert own_action['mode']=='action-guidance' and own_action['executed'] is False
        recipes_admin=client.get('/api/ai/copilot/workflows',headers=admin)
        recipes_staff=client.get('/api/ai/copilot/workflows',headers=staff)
        assert recipes_admin.status_code==recipes_staff.status_code==200
        for result,header in [(recipes_admin,admin),(recipes_staff,staff)]:
            obj=result.json()
            available={f['key'] for f in client.get('/api/ai/copilot/features',headers=header).json()}
            assert len(obj['workflows'])>=4 and all(len(w['steps'])>=2 for w in obj['workflows'])
            assert all(step['feature_key'] in available and not step.get('executed')
                       for flow in obj['workflows'] for step in flow['steps'])
            assert all(flow['guide_only'] for flow in obj['workflows'])
        assert not any(step['feature_key'] in ('accounts','audit','developer')
                       for flow in recipes_staff.json()['workflows'] for step in flow['steps'])
        with main.db() as c:
            assert c.execute('SELECT COUNT(*) FROM ai_action_proposals').fetchone()[0]==0
            assert c.execute('SELECT COUNT(*) FROM audit_events WHERE action LIKE "ai.action%"').fetchone()[0]==0
        print('PASS AI v8: 73-feature command planning, role-scoped multi-module guides, no unconfirmed writes, protected screens')
